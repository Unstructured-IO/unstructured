"""Defines Abstract Base Classes (ABC's) core to batch processing documents
through Unstructured."""

import functools
import json
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Type

import click
import requests
from jsonschema import validate

from unstructured.documents.elements import DataSourceMetadata
from unstructured.ingest.error import PartitionError, SourceConnectionError
from unstructured.ingest.logger import logger
from unstructured.partition.auto import partition
from unstructured.staging.base import convert_to_dict


@dataclass
class BaseSessionHandle(ABC):
    """Abstract Base Class for sharing resources that are local to an individual process.
    e.g., a connection for making a request for fetching documents."""


class BaseConfig(ABC):
    @staticmethod
    @abstractmethod
    def get_schema() -> dict:
        pass

    @classmethod
    def merge_schemas(cls, configs: List[Type["BaseConfig"]]) -> dict:
        base_schema = cls.get_schema()
        for other in configs:
            other_schema = other.get_schema()
            if "required" in base_schema:
                base_schema.get("required", []).extend(other_schema.get("required", []))
            else:
                base_schema["required"] = other_schema.get("required", [])
            if "properties" in other_schema:
                base_schema.get("properties", {}).update(other_schema.get("properties", {}))
            else:
                base_schema["properties"] = other_schema.get("properties", {})
        return base_schema

    @classmethod
    def merge_sample_jsons(cls, configs: List[Type["BaseConfig"]]) -> dict:
        base_json = cls.get_sample_dict()
        for other in configs:
            base_json.update(other.get_sample_dict())
        return base_json

    @classmethod
    def get_sample_dict(cls) -> dict:
        config = cls()
        return config.__dict__

    @staticmethod
    @abstractmethod
    def add_cli_options(cmd: click.Command) -> None:
        pass

    @classmethod
    def from_dict(cls, d: dict):
        schema = cls.get_schema()
        sample_dict = cls.get_sample_dict()
        filtered_dict = {k: v for k, v in d.items() if k in sample_dict}
        validate(filtered_dict, schema=schema)
        return cls(**filtered_dict)


@dataclass
class PartitionConfigs(BaseConfig):
    # where to write structured data outputs
    output_dir: str = "structured-output"
    num_processes: int = 2
    max_docs: Optional[int] = None
    pdf_infer_table_structure: bool = False
    strategy: str = "auto"
    reprocess: bool = False
    ocr_languages: str = "eng"
    encoding: Optional[str] = None
    fields_include: List[str] = field(
        default_factory=lambda: ["element_id", "text", "type", "metadata"],
    )
    flatten_metadata: bool = False
    metadata_exclude: List[str] = field(default_factory=list)
    metadata_include: List[str] = field(default_factory=list)
    partition_endpoint: Optional[str] = None
    api_key: Optional[str] = None

    @staticmethod
    def add_cli_options(cmd: click.Command) -> None:
        options = [
            click.Option(
                ["--output-dir"],
                default="structured-output",
                help="Where to place structured output .json files.",
            ),
            click.Option(
                ["--num-processes"],
                default=2,
                show_default=True,
                help="Number of parallel processes to process docs in.",
            ),
            click.Option(
                ["--max-docs"],
                default=None,
                type=int,
                help="If specified, process at most specified number of documents.",
            ),
            click.Option(
                ["--pdf-infer-table-structure"],
                default=False,
                help="If set to True, partition will include the table's text "
                "content in the response.",
            ),
            click.Option(
                ["--strategy"],
                default="auto",
                help="The method that will be used to process the documents. "
                "Default: auto. Other strategies include `fast` and `hi_res`.",
            ),
            click.Option(
                ["--reprocess"],
                is_flag=True,
                default=False,
                help="Reprocess a downloaded file even if the relevant structured "
                "output .json file in output directory already exists.",
            ),
            click.Option(
                ["--ocr-languages"],
                default="eng",
                help="A list of language packs to specify which languages to use for OCR, "
                "separated by '+' e.g. 'eng+deu' to use the English and German language packs. "
                "The appropriate Tesseract "
                "language pack needs to be installed."
                "Default: eng",
            ),
            click.Option(
                ["--encoding"],
                default=None,
                help="Text encoding to use when reading documents. By default the encoding is "
                "detected automatically.",
            ),
            click.Option(
                ["--fields-include"],
                multiple=True,
                default=["element_id", "text", "type", "metadata"],
                help="If set, include the specified top-level fields in an element. ",
            ),
            click.Option(
                ["--flatten-metadata"],
                is_flag=True,
                default=False,
                help="Results in flattened json elements. "
                "Specifically, the metadata key values are brought to "
                "the top-level of the element, and the `metadata` key itself is removed.",
            ),
            click.Option(
                ["--metadata-include"],
                default=[],
                multiple=True,
                help="If set, include the specified metadata fields if they exist "
                "and drop all other fields. ",
            ),
            click.Option(
                ["--metadata-exclude"],
                default=[],
                multiple=True,
                help="If set, drop the specified metadata fields if they exist. ",
            ),
            click.Option(
                ["--partition-endpoint"],
                default=None,
                help="If provided, will use api to run partition",
            ),
            click.Option(
                ["--api-key"],
                default=None,
                help="API Key for partition endpoint.",
            ),
        ]
        cmd.params.extend(options)

    @staticmethod
    def get_schema() -> dict:
        return {
            "type": "object",
            "properties": {
                "output_dir": {"type": "string", "default": "structured-output"},
                "num_processes": {"type": ["integer", "null"], "default": None},
                "max_docs": {"type": "integer", "default": 2},
                "pdf_infer_table_structure": {"type": "boolean"},
                "strategy": {"type": ["string", "null"], "default": "auto"},
                "reprocess": {"type": "boolean"},
                "ocr_language": {"type": ["string", "null"], "default": "eng"},
                "encoding": {"type": ["string", "null"], "default": None},
                "fields_include": {
                    "type": "array",
                    "items": {
                        "type": "string",
                    },
                },
                "flatten_metadata": {"type": "boolean"},
                "metadata_exclude": {
                    "type": "array",
                    "items": {
                        "type": "string",
                    },
                },
                "metadata_include": {
                    "type": "array",
                    "items": {
                        "type": "string",
                    },
                },
                "partition_endpoint": {"type": ["string", "null"], "default": None},
                "api_key": {"type": ["string", "null"], "default": None},
            },
        }


@dataclass
class ReadConfigs(BaseConfig):
    # where raw documents are stored for processing, and then removed if not preserve_downloads
    download_dir: Optional[str] = None
    re_download: bool = False

    @staticmethod
    def add_cli_options(cmd: click.Command) -> None:
        options = [
            click.Option(
                ["--download-dir"],
                help="Where files are downloaded to, defaults to a location at"
                "`$HOME/.cache/unstructured/ingest/<connector name>/<SHA256>`.",
            ),
            click.Option(
                ["--re-download"],
                is_flag=True,
                default=False,
                help="Re-download files even if they are already present in download dir.",
            ),
        ]
        cmd.params.extend(options)

    @staticmethod
    def get_schema() -> dict:
        return {
            "type": "object",
            "properties": {
                "download_dir": {"type": ["string", "null"], "default": None},
                "re_download": {"type": "boolean"},
            },
        }


@dataclass
class ProcessorConfigs:
    """Common set of config required when running data connectors."""

    partition_strategy: str
    partition_ocr_languages: str
    partition_pdf_infer_table_structure: bool
    partition_encoding: str
    num_processes: int
    reprocess: bool
    max_docs: int


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
    api_key: str = ""
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
    @abstractmethod
    def _output_filename(self):
        """Filename of the structured output for this doc."""

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

    @staticmethod
    def skip_if_file_exists(func):
        """Decorator that checks if a file exists, is not empty, and should not re-download,
        if so log a message indicating as much and skip the decorated function."""

        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            if (
                not self.standard_config.re_download
                and self.filename.is_file()
                and self.filename.stat().st_size
            ):
                logger.debug(f"File exists: {self.filename}, skipping {func.__name__}")
                return None
            return func(self, *args, **kwargs)

        return wrapper

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

    def write_result(self):
        """Write the structured json result for this doc. result must be json serializable."""
        if self.standard_config.download_only:
            return
        self._output_filename.parent.mkdir(parents=True, exist_ok=True)
        with open(self._output_filename, "w", encoding="utf8") as output_f:
            json.dump(self.isd_elems_no_filename, output_f, ensure_ascii=False, indent=2)
        logger.info(f"Wrote {self._output_filename}")

    @PartitionError.wrap
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
                headers_dict = {}
                if len(self.standard_config.api_key) > 0:
                    headers_dict["UNSTRUCTURED-API-KEY"] = self.standard_config.api_key
                response = requests.post(
                    f"{endpoint}",
                    files={"files": (str(self.filename), f)},
                    headers=headers_dict,
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
                        for f in nested_fields[:-1]:
                            if f in current_elem:
                                current_elem = current_elem[f]
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


class ConnectorCleanupMixin:
    standard_config: StandardConnectorConfig

    def cleanup(self, cur_dir=None):
        """Recursively clean up downloaded files and directories."""
        if self.standard_config.preserve_downloads or self.standard_config.download_only:
            return
        if cur_dir is None:
            cur_dir = self.standard_config.download_dir
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
    standard_config: StandardConnectorConfig

    @property
    @abstractmethod
    def filename(self):
        """The local filename of the document after fetching from remote source."""

    def cleanup_file(self):
        """Removes the local copy of the file after successful processing."""
        if (
            not self.standard_config.preserve_downloads
            and self.filename.is_file()
            and not self.standard_config.download_only
        ):
            logger.debug(f"Cleaning up {self}")
            os.unlink(self.filename)


class ConfigSessionHandleMixin:
    @abstractmethod
    def create_session_handle(self) -> BaseSessionHandle:
        """Creates a session handle that will be assigned on each IngestDoc to share
        session related resources across all document handling for a given subprocess."""


class IngestDocSessionHandleMixin:
    config: ConfigSessionHandleMixin
    _session_handle: Optional[BaseSessionHandle] = None

    @property
    def session_handle(self):
        """If a session handle is not assigned, creates a new one and assigns it."""
        if self._session_handle is None:
            self._session_handle = self.config.create_session_handle()
        return self._session_handle

    @session_handle.setter
    def session_handle(self, session_handle: BaseSessionHandle):
        self._session_handle = session_handle
