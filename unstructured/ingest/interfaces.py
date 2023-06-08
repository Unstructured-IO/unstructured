"""Defines Abstract Base Classes (ABC's) core to batch processing documents
through Unstructured."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

import requests

from unstructured.documents.elements import DataSourceMetadata
from unstructured.ingest.logger import logger
from unstructured.partition.auto import partition
from unstructured.staging.base import convert_to_dict


@dataclass
class StandardConnectorConfig:
    """Common set of config options passed to all connectors."""

    # where raw documents are stored for processing, and then removed if not preserve_downloads
    download_dir: str
    # where to write structured data outputs
    output_dir: str
    download_only: bool = False
    fields_include: str = "element_id,text,type,metadata"
    flatten_metadata: bool = False
    metadata_exclude: Optional[str] = None
    metadata_include: Optional[str] = None
    partition_by_api: bool = False
    partition_endpoint: str = "https://api.unstructured.io/general/v0/general"
    preserve_downloads: bool = False
    re_download: bool = False


class BaseConnectorConfig(ABC):
    """Abstract definition on which to define connector-specific attributes."""


@dataclass
class BaseConnector(ABC):
    """Abstract Base Class for a connector to a remote source, e.g. S3 or Google Drive."""

    standard_config: StandardConnectorConfig
    config: BaseConnectorConfig

    def __init__(self, standard_config: StandardConnectorConfig, config: BaseConnectorConfig):
        """Expects a standard_config object that implements StandardConnectorConfig
        and config object that implements BaseConnectorConfig."""
        self.standard_config = standard_config
        self.config = config

    @abstractmethod
    def cleanup(self, cur_dir=None):
        """Any additional cleanup up need after processing is complete. E.g., removing
        temporary download dirs that are empty.

        By convention, documents that failed to process are typically not cleaned up."""
        pass

    @abstractmethod
    def initialize(self):
        """Initializes the connector. Should also validate the connector is properly
        configured: e.g., list a single a document from the source."""
        pass

    @abstractmethod
    def get_ingest_docs(self):
        """Returns all ingest docs (derived from BaseIngestDoc).
        This does not imply downloading all the raw documents themselves,
        rather each IngestDoc is capable of fetching its content (in another process)
        with IngestDoc.get_file()."""
        pass


@dataclass
class BaseIngestDoc(ABC):
    """An "ingest document" is specific to a connector, and provides
    methods to fetch a single raw document, store it locally for processing, any cleanup
    needed after successful processing of the doc, and the ability to write the doc's
    structured outputs once processed.

    Crucially, it is not responsible for the actual processing of the raw document.
    """

    standard_config: StandardConnectorConfig
    config: BaseConnectorConfig

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._date_processed = None

    @property
    def date_created(self) -> Optional[str]:
        """The date the document was created on the source system."""
        return None

    @property
    def date_modified(self) -> Optional[str]:
        """The date the document was last modified on the source system."""
        return None

    @property
    def date_processed(self) -> Optional[str]:
        """The date the document was last processed by Unstructured.
        self._date_processed is assigned internally in self.partition_file()"""
        return self._date_processed

    @property
    def exists(self) -> Optional[bool]:
        """Whether the document exists on the remote source."""
        return None

    @property
    @abstractmethod
    def filename(self):
        """The local filename of the document after fetching from remote source."""

    @property
    def record_locator(self) -> Optional[Dict[str, Any]]:  # Values must be JSON-serializable
        """A dictionary with any data necessary to uniquely identify the document on
        the source system."""
        return None

    @property
    def source_url(self) -> Optional[str]:
        """The url of the source document."""
        return None

    @property
    def version(self) -> Optional[str]:
        """The version of the source document, this could be the last modified date, an
        explicit version number, or anything else that can be used to uniquely identify
        the version of the document."""
        return None

    @abstractmethod
    def cleanup_file(self):
        """Removes the local copy the file (or anything else) after successful processing."""
        pass

    # NOTE(crag): Future BaseIngestDoc classes could define get_file_object() methods
    # in addition to or instead of get_file()
    @abstractmethod
    def get_file(self):
        """Fetches the "remote" doc and stores it locally on the filesystem."""
        pass

    @abstractmethod
    def has_output(self) -> bool:
        """Determine if structured output for this doc already exists."""
        pass

    @abstractmethod
    def write_result(self):
        """Write the structured json result for this doc. result must be json serializable."""
        pass

    def partition_file(self, **partition_kwargs) -> List[Dict[str, Any]]:
        if not self.standard_config.partition_by_api:
            logger.debug("Using local partition")
            elements = partition(
                filename=str(self.filename),
                data_source_metadata=DataSourceMetadata(
                    url=self.source_url,
                    version=self.version,
                    record_locator=self.record_locator,
                    date_created=self.date_created,
                    date_modified=self.date_modified,
                    date_processed=self.date_processed,
                ),
                **partition_kwargs,
            )
            return convert_to_dict(elements)

        else:
            endpoint = self.standard_config.partition_endpoint

            logger.debug(f"Using remote partition ({endpoint})")

            with open(self.filename, "rb") as f:
                response = requests.post(
                    f"{endpoint}",
                    files={"files": (str(self.filename), f)},
                    # TODO: add m_data_source_metadata to unstructured-api pipeline_api and then
                    # pass the stringified json here
                )

            if response.status_code != 200:
                raise RuntimeError(f"Caught {response.status_code} from API: {response.text}")

            return response.json()

    def process_file(self, **partition_kwargs) -> Optional[List[Dict[str, Any]]]:
        self._date_processed = datetime.utcnow().isoformat()
        if self.standard_config.download_only:
            return None
        logger.info(f"Processing {self.filename}")

        isd_elems = self.partition_file(**partition_kwargs)

        self.isd_elems_no_filename = []
        for elem in isd_elems:
            # type: ignore
            if (
                self.standard_config.metadata_exclude is not None
                and self.standard_config.metadata_include is not None
            ):
                raise ValueError(
                    "Arguments `--metadata-include` and `--metadata-exclude` are "
                    "mutually exclusive with each other.",
                )
            elif self.standard_config.metadata_exclude is not None:
                ex_list = self.standard_config.metadata_exclude.split(",")
                for ex in ex_list:
                    if "." in ex:  # handle nested fields
                        nested_fields = ex.split(".")
                        current_elem = elem
                        for field in nested_fields[:-1]:
                            if field in current_elem:
                                current_elem = current_elem[field]
                        field_to_exclude = nested_fields[-1]
                        if field_to_exclude in current_elem:
                            current_elem.pop(field_to_exclude, None)
                    else:  # handle top-level fields
                        elem["metadata"].pop(ex, None)  # type: ignore[attr-defined]
            elif self.standard_config.metadata_include is not None:
                in_list = self.standard_config.metadata_include.split(",")
                for k in list(elem["metadata"].keys()):  # type: ignore[attr-defined]
                    if k not in in_list:
                        elem["metadata"].pop(k, None)  # type: ignore[attr-defined]

            in_list = self.standard_config.fields_include.split(",")
            elem = {k: v for k, v in elem.items() if k in in_list}

            if self.standard_config.flatten_metadata:
                for k, v in elem["metadata"].items():  # type: ignore[attr-defined]
                    elem[k] = v
                elem.pop("metadata")  # type: ignore[attr-defined]

            self.isd_elems_no_filename.append(elem)

        return self.isd_elems_no_filename
