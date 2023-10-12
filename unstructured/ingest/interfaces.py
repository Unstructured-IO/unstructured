"""Defines Abstract Base Classes (ABC's) core to batch processing documents
through Unstructured."""

import functools
import json
import os
import typing as t
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import requests
from dataclasses_json import DataClassJsonMixin

from unstructured.chunking.title import chunk_by_title
from unstructured.documents.elements import DataSourceMetadata
from unstructured.embed.interfaces import BaseEmbeddingEncoder, Element
from unstructured.embed.openai import OpenAIEmbeddingEncoder
from unstructured.ingest.error import PartitionError, SourceConnectionError
from unstructured.ingest.ingest_doc_json_mixin import IngestDocJsonMixin
from unstructured.ingest.logger import logger
from unstructured.partition.auto import partition
from unstructured.staging.base import convert_to_dict, elements_from_json


@dataclass
class BaseSessionHandle(ABC):
    """Abstract Base Class for sharing resources that are local to an individual process.
    e.g., a connection for making a request for fetching documents."""


class BaseConfig(DataClassJsonMixin, ABC):
    pass


@dataclass
class PartitionConfig(BaseConfig):
    # where to write structured data outputs
    pdf_infer_table_structure: bool = False
    skip_infer_table_types: t.Optional[t.List[str]] = None
    strategy: str = "auto"
    ocr_languages: str = "eng"
    encoding: t.Optional[str] = None
    fields_include: t.List[str] = field(
        default_factory=lambda: ["element_id", "text", "type", "metadata", "embeddings"],
    )
    flatten_metadata: bool = False
    metadata_exclude: t.List[str] = field(default_factory=list)
    metadata_include: t.List[str] = field(default_factory=list)
    partition_endpoint: t.Optional[str] = None
    partition_by_api: bool = False
    api_key: t.Optional[str] = None


@dataclass
class ProcessorConfig(BaseConfig):
    reprocess: bool = False
    verbose: bool = False
    work_dir: str = str((Path.home() / ".cache" / "unstructured" / "ingest" / "pipeline").resolve())
    output_dir: str = "structured-output"
    num_processes: int = 2


@dataclass
class ReadConfig(BaseConfig):
    # where raw documents are stored for processing, and then removed if not preserve_downloads
    download_dir: str = ""
    re_download: bool = False
    preserve_downloads: bool = False
    download_only: bool = False
    max_docs: t.Optional[int] = None


@dataclass
class EmbeddingConfig(BaseConfig):
    api_key: str
    model_name: t.Optional[str] = None

    def get_embedder(self) -> BaseEmbeddingEncoder:
        # TODO update to incorporate other embedder types once they exist
        kwargs = {
            "api_key": self.api_key,
        }
        if self.model_name:
            kwargs["model_name"] = self.model_name
        return OpenAIEmbeddingEncoder(**kwargs)


@dataclass
class ChunkingConfig(BaseConfig):
    chunk_elements: bool = False
    multipage_sections: bool = True
    combine_text_under_n_chars: int = 500
    max_characters: int = 1500

    def chunk(self, elements: t.List[Element]) -> t.List[Element]:
        if self.chunk_elements:
            return chunk_by_title(
                elements=elements,
                multipage_sections=self.multipage_sections,
                combine_text_under_n_chars=self.combine_text_under_n_chars,
                max_characters=self.max_characters,
            )
        else:
            return elements


@dataclass
class WriteConfig(BaseConfig):
    pass


class BaseConnectorConfig(ABC):
    """Abstract definition on which to define connector-specific attributes."""


@dataclass
class SourceMetadata(DataClassJsonMixin, ABC):
    date_created: t.Optional[str] = None
    date_modified: t.Optional[str] = None
    version: t.Optional[str] = None
    source_url: t.Optional[str] = None
    exists: t.Optional[bool] = None


@dataclass
class BaseIngestDoc(IngestDocJsonMixin, ABC):
    """An "ingest document" is specific to a connector, and provides
    methods to fetch a single raw document, store it locally for processing, any cleanup
    needed after successful processing of the doc, and the ability to write the doc's
    structured outputs once processed.

    Crucially, it is not responsible for the actual processing of the raw document.
    """

    processor_config: ProcessorConfig
    read_config: ReadConfig
    connector_config: BaseConnectorConfig
    _source_metadata: t.Optional[SourceMetadata] = field(init=False, default=None)
    _date_processed: t.Optional[str] = field(init=False, default=None)

    @property
    def source_metadata(self) -> SourceMetadata:
        if self._source_metadata is None:
            self.update_source_metadata()
        # Provide guarantee that the field was set by update_source_metadata()
        if self._source_metadata is None:
            raise ValueError("failed to set source metadata")
        return self._source_metadata

    @source_metadata.setter
    def source_metadata(self, value: SourceMetadata):
        self._source_metadata = value

    @property
    def date_created(self) -> t.Optional[str]:
        """The date the document was created on the source system."""
        return self.source_metadata.date_created  # type: ignore

    @property
    def date_modified(self) -> t.Optional[str]:
        """The date the document was last modified on the source system."""
        return self.source_metadata.date_modified  # type: ignore

    @property
    def date_processed(self) -> t.Optional[str]:
        """The date the document was last processed by Unstructured.
        self._date_processed is assigned internally in self.partition_file()"""
        return self._date_processed  # type: ignore

    @property
    def exists(self) -> t.Optional[bool]:
        """Whether the document exists on the remote source."""
        return self.source_metadata.exists  # type: ignore

    @property
    @abstractmethod
    def filename(self):
        """The local filename of the document after fetching from remote source."""

    @property
    def base_filename(self) -> t.Optional[str]:
        if self.read_config.download_dir and self.filename:
            download_path = str(Path(self.read_config.download_dir).resolve())
            full_path = str(self.filename)
            base_path = full_path.replace(download_path, "")
            return base_path
        return None

    @property
    @abstractmethod
    def _output_filename(self):
        """Filename of the structured output for this doc."""

    @property
    def record_locator(self) -> t.Optional[t.Dict[str, t.Any]]:  # Values must be JSON-serializable
        """A dictionary with any data necessary to uniquely identify the document on
        the source system."""
        return None

    @property
    def source_url(self) -> t.Optional[str]:
        """The url of the source document."""
        return self.source_metadata.source_url  # type: ignore

    @property
    def version(self) -> t.Optional[str]:
        """The version of the source document, this could be the last modified date, an
        explicit version number, or anything else that can be used to uniquely identify
        the version of the document."""
        return self.source_metadata.version  # type: ignore

    @abstractmethod
    def cleanup_file(self):
        """Removes the local copy the file (or anything else) after successful processing."""
        pass

    @staticmethod
    def skip_if_file_exists(func):
        """Decorator that checks if a file exists, is not empty, and should not re-download,
        if so log a message indicating as much and skip the decorated function."""

        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            if (
                not self.read_config.re_download
                and self.filename.is_file()
                and self.filename.stat().st_size
            ):
                logger.debug(f"File exists: {self.filename}, skipping {func.__name__}")
                return None
            return func(self, *args, **kwargs)

        return wrapper

    # TODO: set as @abstractmethod and pass or raise NotImplementedError
    def update_source_metadata(self, **kwargs) -> None:
        """Sets the SourceMetadata and the  properties for the doc"""
        self._source_metadata = SourceMetadata()

    # NOTE(crag): Future BaseIngestDoc classes could define get_file_object() methods
    # in addition to or instead of get_file()
    @abstractmethod
    @SourceConnectionError.wrap
    def get_file(self):
        """Fetches the "remote" doc and stores it locally on the filesystem."""
        pass

    def has_output(self) -> bool:
        """Determine if structured output for this doc already exists."""
        return self._output_filename.is_file() and self._output_filename.stat().st_size

    @PartitionError.wrap
    def partition_file(
        self,
        partition_config: PartitionConfig,
        **partition_kwargs,
    ) -> t.List[Element]:
        if not partition_config.partition_by_api:
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
        else:
            endpoint = partition_config.partition_endpoint

            logger.debug(f"Using remote partition ({endpoint})")

            with open(self.filename, "rb") as f:
                headers_dict = {}
                if partition_config.api_key:
                    headers_dict["UNSTRUCTURED-API-KEY"] = partition_config.api_key
                response = requests.post(
                    f"{endpoint}",
                    files={"files": (str(self.filename), f)},
                    headers=headers_dict,
                    # TODO: add m_data_source_metadata to unstructured-api pipeline_api and then
                    # pass the stringified json here
                )

            if response.status_code != 200:
                raise RuntimeError(f"Caught {response.status_code} from API: {response.text}")
            elements = elements_from_json(text=json.dumps(response.json()))
        return elements

    def process_file(
        self,
        partition_config: PartitionConfig,
        **partition_kwargs,
    ) -> t.Optional[t.List[t.Dict[str, t.Any]]]:
        self._date_processed = datetime.utcnow().isoformat()
        if self.read_config.download_only:
            return None
        logger.info(f"Processing {self.filename}")

        isd_elems_raw = self.partition_file(partition_config=partition_config, **partition_kwargs)
        isd_elems = convert_to_dict(isd_elems_raw)

        self.isd_elems_no_filename: t.List[t.Dict[str, t.Any]] = []
        for elem in isd_elems:
            # type: ignore
            if partition_config.metadata_exclude and partition_config.metadata_include:
                raise ValueError(
                    "Arguments `--metadata-include` and `--metadata-exclude` are "
                    "mutually exclusive with each other.",
                )
            elif partition_config.metadata_exclude:
                ex_list = partition_config.metadata_exclude
                for ex in ex_list:
                    if "." in ex:  # handle nested fields
                        nested_fields = ex.split(".")
                        current_elem = elem
                        for f in nested_fields[:-1]:
                            if f in current_elem:
                                current_elem = current_elem[f]
                        field_to_exclude = nested_fields[-1]
                        if field_to_exclude in current_elem:
                            current_elem.pop(field_to_exclude, None)
                    else:  # handle top-level fields
                        elem["metadata"].pop(ex, None)  # type: ignore[attr-defined]
            elif partition_config.metadata_include:
                in_list = partition_config.metadata_include
                for k in list(elem["metadata"].keys()):  # type: ignore[attr-defined]
                    if k not in in_list:
                        elem["metadata"].pop(k, None)  # type: ignore[attr-defined]
            in_list = partition_config.fields_include
            elem = {k: v for k, v in elem.items() if k in in_list}

            if partition_config.flatten_metadata:
                for k, v in elem["metadata"].items():  # type: ignore[attr-defined]
                    elem[k] = v
                elem.pop("metadata")  # type: ignore[attr-defined]

            self.isd_elems_no_filename.append(elem)

        return self.isd_elems_no_filename


@dataclass
class BaseSourceConnector(DataClassJsonMixin, ABC):
    """Abstract Base Class for a connector to a remote source, e.g. S3 or Google Drive."""

    processor_config: ProcessorConfig
    read_config: ReadConfig
    connector_config: BaseConnectorConfig

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
class BaseDestinationConnector(DataClassJsonMixin, ABC):
    write_config: WriteConfig
    connector_config: BaseConnectorConfig

    def __init__(self, write_config: WriteConfig, connector_config: BaseConnectorConfig):
        self.write_config = write_config
        self.connector_config = connector_config

    @abstractmethod
    def initialize(self):
        """Initializes the connector. Should also validate the connector is properly
        configured."""
        pass

    @abstractmethod
    def write(self, docs: t.List[BaseIngestDoc]) -> None:
        pass


class SourceConnectorCleanupMixin:
    read_config: ReadConfig

    def cleanup(self, cur_dir=None):
        """Recursively clean up downloaded files and directories."""
        if self.read_config.preserve_downloads or self.read_config.download_only:
            return
        if cur_dir is None:
            cur_dir = self.read_config.download_dir
        if cur_dir is None or not Path(cur_dir).is_dir():
            return
        sub_dirs = os.listdir(cur_dir)
        os.chdir(cur_dir)
        for sub_dir in sub_dirs:
            # don't traverse symlinks, not that there every should be any
            if os.path.isdir(sub_dir) and not os.path.islink(sub_dir):
                self.cleanup(sub_dir)
        os.chdir("..")
        if len(os.listdir(cur_dir)) == 0:
            os.rmdir(cur_dir)


class IngestDocCleanupMixin:
    read_config: ReadConfig

    @property
    @abstractmethod
    def filename(self):
        """The local filename of the document after fetching from remote source."""

    def cleanup_file(self):
        """Removes the local copy of the file after successful processing."""
        if (
            not self.read_config.preserve_downloads
            and self.filename.is_file()
            and not self.read_config.download_only
        ):
            logger.debug(f"Cleaning up {self}")
            os.unlink(self.filename)


class ConfigSessionHandleMixin:
    @abstractmethod
    def create_session_handle(self) -> BaseSessionHandle:
        """Creates a session handle that will be assigned on each IngestDoc to share
        session related resources across all document handling for a given subprocess."""


class IngestDocSessionHandleMixin:
    connector_config: ConfigSessionHandleMixin
    _session_handle: t.Optional[BaseSessionHandle] = None

    @property
    def session_handle(self):
        """If a session handle is not assigned, creates a new one and assigns it."""
        if self._session_handle is None:
            self._session_handle = self.connector_config.create_session_handle()
        return self._session_handle

    @session_handle.setter
    def session_handle(self, session_handle: BaseSessionHandle):
        self._session_handle = session_handle
