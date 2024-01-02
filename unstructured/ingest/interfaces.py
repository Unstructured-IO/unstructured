"""Defines Abstract Base Classes (ABC's) core to batch processing documents
through Unstructured."""

import functools
import os
import re
import typing as t
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from dataclasses_json import DataClassJsonMixin
from dataclasses_json.core import Json, _decode_dataclass

from unstructured.chunking.title import chunk_by_title
from unstructured.documents.elements import DataSourceMetadata
from unstructured.embed.interfaces import BaseEmbeddingEncoder, Element
from unstructured.ingest.enhanced_dataclass import EnhancedDataClassJsonMixin, enhanced_field
from unstructured.ingest.enhanced_dataclass.core import _asdict
from unstructured.ingest.error import PartitionError, SourceConnectionError
from unstructured.ingest.logger import logger
from unstructured.partition.api import partition_via_api
from unstructured.partition.auto import partition
from unstructured.staging.base import convert_to_dict, flatten_dict

A = t.TypeVar("A", bound="DataClassJsonMixin")

SUPPORTED_REMOTE_FSSPEC_PROTOCOLS = [
    "s3",
    "s3a",
    "abfs",
    "az",
    "gs",
    "gcs",
    "box",
    "dropbox",
    "sftp",
]


@dataclass
class BaseSessionHandle(ABC):
    """Abstract Base Class for sharing resources that are local to an individual process.
    e.g., a connection for making a request for fetching documents."""


@dataclass
class BaseConfig(EnhancedDataClassJsonMixin, ABC):
    pass


@dataclass
class AccessConfig(BaseConfig):
    # Meant to designate holding any sensitive information associated with other configs
    pass


@dataclass
class RetryStrategyConfig(BaseConfig):
    """
    Contains all info needed for decorator to pull from `self` for backoff
    and retry triggered by exception.

    Args:
        max_retries: The maximum number of attempts to make before giving
            up. Once exhausted, the exception will be allowed to escape.
            The default value of None means there is no limit to the
            number of tries. If a callable is passed, it will be
            evaluated at runtime and its return value used.
        max_retry_time: The maximum total amount of time to try for before
            giving up. Once expired, the exception will be allowed to
            escape. If a callable is passed, it will be
            evaluated at runtime and its return value used.
    """

    max_retries: t.Optional[int] = None
    max_retry_time: t.Optional[float] = None


@dataclass
class PartitionConfig(BaseConfig):
    # where to write structured data outputs
    pdf_infer_table_structure: bool = False
    strategy: str = "auto"
    ocr_languages: t.Optional[t.List[str]] = None
    encoding: t.Optional[str] = None
    additional_partition_args: dict = field(default_factory=dict)
    skip_infer_table_types: t.Optional[t.List[str]] = None
    fields_include: t.List[str] = field(
        default_factory=lambda: ["element_id", "text", "type", "metadata", "embeddings"],
    )
    flatten_metadata: bool = False
    metadata_exclude: t.List[str] = field(default_factory=list)
    metadata_include: t.List[str] = field(default_factory=list)
    partition_endpoint: t.Optional[str] = "https://api.unstructured.io/general/v0/general"
    partition_by_api: bool = False
    api_key: t.Optional[str] = enhanced_field(default=None, sensitive=True)
    hi_res_model_name: t.Optional[str] = None


@dataclass
class ProcessorConfig(BaseConfig):
    reprocess: bool = False
    verbose: bool = False
    work_dir: str = str((Path.home() / ".cache" / "unstructured" / "ingest" / "pipeline").resolve())
    output_dir: str = "structured-output"
    num_processes: int = 2
    raise_on_error: bool = False


@dataclass
class FileStorageConfig(BaseConfig):
    remote_url: str
    uncompress: bool = False
    recursive: bool = False
    file_glob: t.Optional[t.List[str]] = None


@dataclass
class FsspecConfig(FileStorageConfig):
    access_config: AccessConfig = None
    protocol: str = field(init=False)
    path_without_protocol: str = field(init=False)
    dir_path: str = field(init=False)
    file_path: str = field(init=False)

    def get_access_config(self) -> dict:
        if self.access_config:
            return self.access_config.to_dict(apply_name_overload=False)
        else:
            return {}

    def __post_init__(self):
        self.protocol, self.path_without_protocol = self.remote_url.split("://")
        if self.protocol not in SUPPORTED_REMOTE_FSSPEC_PROTOCOLS:
            raise ValueError(
                f"Protocol {self.protocol} not supported yet, only "
                f"{SUPPORTED_REMOTE_FSSPEC_PROTOCOLS} are supported.",
            )

        # dropbox root is an empty string
        match = re.match(rf"{self.protocol}://([\s])/", self.remote_url)
        if match and self.protocol == "dropbox":
            self.dir_path = " "
            self.file_path = ""
            return

        # dropbox paths can start with slash
        match = re.match(rf"{self.protocol}:///([^/\s]+?)/([^\s]*)", self.remote_url)
        if match and self.protocol == "dropbox":
            self.dir_path = match.group(1)
            self.file_path = match.group(2) or ""
            return

        # just a path with no trailing prefix
        match = re.match(rf"{self.protocol}://([^/\s]+?)(/*)$", self.remote_url)
        if match:
            self.dir_path = match.group(1)
            self.file_path = ""
            return

        # valid path with a dir and/or file
        match = re.match(rf"{self.protocol}://([^/\s]+?)/([^\s]*)", self.remote_url)
        if not match:
            raise ValueError(
                f"Invalid path {self.remote_url}. "
                f"Expected <protocol>://<dir-path>/<file-or-dir-path>.",
            )
        self.dir_path = match.group(1)
        self.file_path = match.group(2) or ""


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
    provider: str
    api_key: t.Optional[str] = enhanced_field(default=None, sensitive=True)
    model_name: t.Optional[str] = None

    def get_embedder(self) -> BaseEmbeddingEncoder:
        kwargs = {}
        if self.api_key:
            kwargs["api_key"] = self.api_key
        if self.model_name:
            kwargs["model_name"] = self.model_name
        # TODO make this more dynamic to map to encoder configs
        if self.provider == "langchain-openai":
            from unstructured.embed.openai import OpenAiEmbeddingConfig, OpenAIEmbeddingEncoder

            return OpenAIEmbeddingEncoder(config=OpenAiEmbeddingConfig(**kwargs))
        elif self.provider == "langchain-huggingface":
            from unstructured.embed.huggingface import (
                HuggingFaceEmbeddingConfig,
                HuggingFaceEmbeddingEncoder,
            )

            return HuggingFaceEmbeddingEncoder(config=HuggingFaceEmbeddingConfig(**kwargs))
        else:
            raise ValueError(f"{self.provider} not a recognized encoder")


@dataclass
class ChunkingConfig(BaseConfig):
    chunk_elements: bool = False
    multipage_sections: bool = True
    combine_text_under_n_chars: int = 500
    max_characters: int = 1500
    new_after_n_chars: t.Optional[int] = None

    def chunk(self, elements: t.List[Element]) -> t.List[Element]:
        if self.chunk_elements:
            return chunk_by_title(
                elements=elements,
                multipage_sections=self.multipage_sections,
                combine_text_under_n_chars=self.combine_text_under_n_chars,
                max_characters=self.max_characters,
                new_after_n_chars=self.new_after_n_chars,
            )
        else:
            return elements


@dataclass
class PermissionsConfig(BaseConfig):
    application_id: t.Optional[str] = enhanced_field(overload_name="permissions_application_id")
    tenant: t.Optional[str] = enhanced_field(overload_name="permissions_tenant")
    client_cred: t.Optional[str] = enhanced_field(
        default=None, sensitive=True, overload_name="permissions_client_cred"
    )


# module-level variable to store session handle
global_write_session_handle: t.Optional[BaseSessionHandle] = None


@dataclass
class WriteConfig(BaseConfig):
    pass


@dataclass
class BaseConnectorConfig(BaseConfig, ABC):
    """Abstract definition on which to define connector-specific attributes."""


@dataclass
class SourceMetadata(EnhancedDataClassJsonMixin, ABC):
    date_created: t.Optional[str] = None
    date_modified: t.Optional[str] = None
    version: t.Optional[str] = None
    source_url: t.Optional[str] = None
    exists: t.Optional[bool] = None
    permissions_data: t.Optional[t.List[t.Dict[str, t.Any]]] = None


class IngestDocJsonMixin(EnhancedDataClassJsonMixin):
    """
    Inherently, DataClassJsonMixin does not add in any @property fields to the json/dict
    created from the dataclass. This explicitly sets properties to look for on the IngestDoc
    class when creating the json/dict for serialization purposes.
    """

    metadata_properties = [
        "date_created",
        "date_modified",
        "date_processed",
        "exists",
        "permissions_data",
        "version",
        "source_url",
    ]
    properties_to_serialize = [
        "base_filename",
        "filename",
        "_output_filename",
        "record_locator",
        "_source_metadata",
        "unique_id",
    ]

    def add_props(self, as_dict: dict, props: t.List[str]):
        for prop in props:
            val = getattr(self, prop)
            if isinstance(val, Path):
                val = str(val)
            if isinstance(val, DataClassJsonMixin):
                val = val.to_dict(encode_json=False)
            as_dict[prop] = val

    def to_dict(self, **kwargs) -> t.Dict[str, Json]:
        as_dict = _asdict(self, **kwargs)
        self.add_props(as_dict=as_dict, props=self.properties_to_serialize)
        if getattr(self, "_source_metadata") is not None:
            self.add_props(as_dict=as_dict, props=self.metadata_properties)
        return as_dict

    @classmethod
    def from_dict(
        cls: t.Type[A], kvs: Json, *, infer_missing=False, apply_name_overload: bool = True
    ) -> A:
        doc = super().from_dict(
            kvs=kvs, infer_missing=infer_missing, apply_name_overload=apply_name_overload
        )
        if meta := kvs.get("_source_metadata"):
            setattr(doc, "_source_metadata", SourceMetadata.from_dict(meta))
        if date_processed := kvs.get("_date_processed"):
            setattr(doc, "_date_processed", date_processed)
        return doc


class BatchIngestDocJsonMixin(EnhancedDataClassJsonMixin):
    """
    Inherently, DataClassJsonMixin does not add in any @property fields to the json/dict
    created from the dataclass. This explicitly sets properties to look for on the IngestDoc
    class when creating the json/dict for serialization purposes.
    """

    properties_to_serialize = ["unique_id"]

    def add_props(self, as_dict: dict, props: t.List[str]):
        for prop in props:
            val = getattr(self, prop)
            if isinstance(val, Path):
                val = str(val)
            if isinstance(val, DataClassJsonMixin):
                val = val.to_dict(encode_json=False)
            as_dict[prop] = val

    def to_dict(self, encode_json=False) -> t.Dict[str, Json]:
        as_dict = _asdict(self, encode_json=encode_json)
        self.add_props(as_dict=as_dict, props=self.properties_to_serialize)
        return as_dict

    @classmethod
    def from_dict(cls: t.Type[A], kvs: Json, *, infer_missing=False) -> A:
        doc = _decode_dataclass(cls, kvs, infer_missing)
        return doc


@dataclass
class BaseIngestDoc(ABC):
    processor_config: ProcessorConfig
    read_config: ReadConfig
    connector_config: BaseConnectorConfig

    @property
    @abstractmethod
    def unique_id(self) -> str:
        pass


@dataclass
class BaseSingleIngestDoc(BaseIngestDoc, IngestDocJsonMixin, ABC):
    """An "ingest document" is specific to a connector, and provides
    methods to fetch a single raw document, store it locally for processing, any cleanup
    needed after successful processing of the doc, and the ability to write the doc's
    structured outputs once processed.

    Crucially, it is not responsible for the actual processing of the raw document.
    """

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
    def base_output_filename(self) -> t.Optional[str]:
        if self.processor_config.output_dir and self._output_filename:
            output_path = str(Path(self.processor_config.output_dir).resolve())
            full_path = str(self._output_filename)
            base_path = full_path.replace(output_path, "")
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
    def unique_id(self) -> str:
        return self.filename

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

    @property
    def permissions_data(self) -> t.Optional[t.List[t.Dict[str, t.Any]]]:
        """Access control data, aka permissions or sharing, from the source system."""
        if self.source_metadata is None:
            self.update_source_metadata()
        return self.source_metadata.permissions_data  # type: ignore

    @abstractmethod
    def cleanup_file(self):
        """Removes the local copy the file (or anything else) after successful processing."""

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

    def update_permissions_data(self):
        """Sets the _permissions_data property for the doc.
        This property is later used to fill the corresponding SourceMetadata.permissions_data field,
        and after that carries on to the permissions_data property."""
        self._permissions_data: t.Optional[t.List[t.Dict]] = None

    # NOTE(crag): Future BaseIngestDoc classes could define get_file_object() methods
    # in addition to or instead of get_file()
    @abstractmethod
    @SourceConnectionError.wrap
    def get_file(self):
        """Fetches the "remote" doc and stores it locally on the filesystem."""

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
                    permissions_data=self.permissions_data,
                ),
                **partition_kwargs,
            )
        else:
            endpoint = partition_config.partition_endpoint

            logger.debug(f"Using remote partition ({endpoint})")

            passthrough_partition_kwargs = {
                k: str(v) for k, v in partition_kwargs.items() if v is not None
            }
            elements = partition_via_api(
                filename=str(self.filename),
                api_key=partition_config.api_key,
                api_url=endpoint,
                **passthrough_partition_kwargs,
            )
            # TODO: add m_data_source_metadata to unstructured-api pipeline_api and then
            # pass the stringified json here
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

            if partition_config.flatten_metadata and "metadata" in elem:
                metadata = elem.pop("metadata")
                elem.update(flatten_dict(metadata, keys_to_omit=["data_source_record_locator"]))

            self.isd_elems_no_filename.append(elem)

        return self.isd_elems_no_filename


@dataclass
class BaseIngestDocBatch(BaseIngestDoc, BatchIngestDocJsonMixin, ABC):
    ingest_docs: t.List[BaseSingleIngestDoc] = field(default_factory=list)

    @abstractmethod
    @SourceConnectionError.wrap
    def get_files(self):
        """Fetches the "remote" docs and stores it locally on the filesystem."""


@dataclass
class BaseConnector(EnhancedDataClassJsonMixin, ABC):
    @abstractmethod
    def check_connection(self):
        pass


@dataclass
class BaseSourceConnector(BaseConnector, ABC):
    """Abstract Base Class for a connector to a remote source, e.g. S3 or Google Drive."""

    processor_config: ProcessorConfig
    read_config: ReadConfig
    connector_config: BaseConnectorConfig

    @abstractmethod
    def cleanup(self, cur_dir=None):
        """Any additional cleanup up need after processing is complete. E.g., removing
        temporary download dirs that are empty.

        By convention, documents that failed to process are typically not cleaned up."""

    @abstractmethod
    def initialize(self):
        """Initializes the connector. Should also validate the connector is properly
        configured: e.g., list a single a document from the source."""

    @abstractmethod
    def get_ingest_docs(self):
        """Returns all ingest docs (derived from BaseIngestDoc).
        This does not imply downloading all the raw documents themselves,
        rather each IngestDoc is capable of fetching its content (in another process)
        with IngestDoc.get_file()."""


@dataclass
class BaseDestinationConnector(BaseConnector, ABC):
    write_config: WriteConfig
    connector_config: BaseConnectorConfig

    def __init__(self, write_config: WriteConfig, connector_config: BaseConnectorConfig):
        self.write_config = write_config
        self.connector_config = connector_config

    @abstractmethod
    def initialize(self):
        """Initializes the connector. Should also validate the connector is properly
        configured."""

    @abstractmethod
    def write(self, docs: t.List[BaseSingleIngestDoc]) -> None:
        pass

    @abstractmethod
    def write_dict(self, *args, elements_dict: t.List[t.Dict[str, t.Any]], **kwargs) -> None:
        pass

    def write_elements(self, elements: t.List[Element], *args, **kwargs) -> None:
        elements_dict = [e.to_dict() for e in elements]
        self.write_dict(*args, elements_dict=elements_dict, **kwargs)


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


class PermissionsCleanupMixin:
    processor_config: ProcessorConfig

    def cleanup_permissions(self, cur_dir=None):
        def has_no_folders(folder_path):
            folders = [
                item
                for item in os.listdir(folder_path)
                if os.path.isdir(os.path.join(folder_path, item))
            ]
            return len(folders) == 0

        """Recursively clean up downloaded files and directories."""
        if cur_dir is None:
            cur_dir = Path(self.processor_config.output_dir, "permissions_data")
        if not Path(cur_dir).exists():
            return
        if Path(cur_dir).is_file():
            cur_file = cur_dir
            os.remove(cur_file)
            return
        sub_dirs = os.listdir(cur_dir)
        os.chdir(cur_dir)
        for sub_dir in sub_dirs:
            # don't traverse symlinks, not that there every should be any
            if not os.path.islink(sub_dir):
                self.cleanup_permissions(sub_dir)
        os.chdir("..")
        if has_no_folders(cur_dir):
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


@dataclass
class IngestDocSessionHandleMixin:
    connector_config: ConfigSessionHandleMixin
    _session_handle: t.Optional[BaseSessionHandle] = field(default=None, init=False)

    @property
    def session_handle(self):
        """If a session handle is not assigned, creates a new one and assigns it."""
        if self._session_handle is None:
            self._session_handle = self.connector_config.create_session_handle()
        return self._session_handle

    @session_handle.setter
    def session_handle(self, session_handle: BaseSessionHandle):
        self._session_handle = session_handle
