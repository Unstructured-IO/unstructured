import os
import re
import typing as t
from contextlib import suppress
from dataclasses import dataclass, field
from pathlib import Path

from unstructured.ingest.error import SourceConnectionError
from unstructured.ingest.interfaces import (
    BaseConnectorConfig,
    BaseDestinationConnector,
    BaseIngestDoc,
    BaseSourceConnector,
    IngestDocCleanupMixin,
    SourceConnectorCleanupMixin,
    SourceMetadata,
)
from unstructured.ingest.logger import logger
from unstructured.utils import (
    requires_dependencies,
)

SUPPORTED_REMOTE_FSSPEC_PROTOCOLS = [
    "s3",
    "s3a",
    "abfs",
    "az",
    "gs",
    "gcs",
    "box",
    "dropbox",
]


@dataclass
class SimpleFsspecConfig(BaseConnectorConfig):
    # fsspec specific options
    path: str
    recursive: bool = False
    access_kwargs: dict = field(default_factory=dict)
    protocol: str = field(init=False)
    path_without_protocol: str = field(init=False)
    dir_path: str = field(init=False)
    file_path: str = field(init=False)

    def get_access_kwargs(self) -> dict:
        return self.access_kwargs

    def __post_init__(self):
        self.protocol, self.path_without_protocol = self.path.split("://")
        if self.protocol not in SUPPORTED_REMOTE_FSSPEC_PROTOCOLS:
            raise ValueError(
                f"Protocol {self.protocol} not supported yet, only "
                f"{SUPPORTED_REMOTE_FSSPEC_PROTOCOLS} are supported.",
            )

        # dropbox root is an empty string
        match = re.match(rf"{self.protocol}://([\s])/", self.path)
        if match and self.protocol == "dropbox":
            self.dir_path = " "
            self.file_path = ""
            return

        # just a path with no trailing prefix
        match = re.match(rf"{self.protocol}://([^/\s]+?)(/*)$", self.path)
        if match:
            self.dir_path = match.group(1)
            self.file_path = ""
            return

        # valid path with a dir and/or file
        match = re.match(rf"{self.protocol}://([^/\s]+?)/([^\s]*)", self.path)
        if not match:
            raise ValueError(
                f"Invalid path {self.path}. Expected <protocol>://<dir-path>/<file-or-dir-path>.",
            )
        self.dir_path = match.group(1)
        self.file_path = match.group(2) or ""


@dataclass
class FsspecIngestDoc(IngestDocCleanupMixin, BaseIngestDoc):
    """Class encapsulating fetching a doc and writing processed results (but not
    doing the processing!).

    Also includes a cleanup method. When things go wrong and the cleanup
    method is not called, the file is left behind on the filesystem to assist debugging.
    """

    connector_config: SimpleFsspecConfig
    remote_file_path: str

    def _tmp_download_file(self):
        download_dir = self.read_config.download_dir if self.read_config.download_dir else ""
        return Path(download_dir) / self.remote_file_path.replace(
            f"{self.connector_config.dir_path}/",
            "",
        )

    @property
    def _output_filename(self):
        return (
            Path(self.partition_config.output_dir)
            / f"{self.remote_file_path.replace(f'{self.connector_config.dir_path}/', '')}.json"
        )

    def _create_full_tmp_dir_path(self):
        """Includes "directories" in the object path"""
        self._tmp_download_file().parent.mkdir(parents=True, exist_ok=True)

    @SourceConnectionError.wrap
    @BaseIngestDoc.skip_if_file_exists
    def get_file(self):
        """Fetches the file from the current filesystem and stores it locally."""
        from fsspec import AbstractFileSystem, get_filesystem_class

        self._create_full_tmp_dir_path()
        fs: AbstractFileSystem = get_filesystem_class(self.connector_config.protocol)(
            **self.connector_config.get_access_kwargs(),
        )
        logger.debug(f"Fetching {self} - PID: {os.getpid()}")
        fs.get(rpath=self.remote_file_path, lpath=self._tmp_download_file().as_posix())
        self.update_source_metadata_metadata()

    @requires_dependencies(["fsspec"])
    def update_source_metadata_metadata(self):
        from fsspec import AbstractFileSystem, get_filesystem_class

        fs: AbstractFileSystem = get_filesystem_class(self.connector_config.protocol)(
            **self.connector_config.get_access_kwargs(),
        )

        date_created = None
        with suppress(NotImplementedError):
            date_created = fs.created(self.remote_file_path).isoformat()

        date_modified = None
        with suppress(NotImplementedError):
            date_modified = fs.modified(self.remote_file_path).isoformat()

        version = (
            fs.checksum(self.remote_file_path)
            if self.connector_config.protocol != "gs"
            else fs.info(self.remote_file_path).get("etag", "")
        )
        file_exists = fs.exists(self.remote_file_path)
        self.source_metadata = SourceMetadata(
            date_created=date_created,
            date_modified=date_modified,
            version=version,
            source_url=f"{self.connector_config.protocol}://{self.remote_file_path}",
            exists=file_exists,
        )

    @property
    def filename(self):
        """The filename of the file after downloading from cloud"""
        return self._tmp_download_file()

    @property
    def record_locator(self) -> t.Optional[t.Dict[str, t.Any]]:
        """Returns the equivalent of ls in dict"""
        return {
            "protocol": self.connector_config.protocol,
            "remote_file_path": self.remote_file_path,
        }


@dataclass
class FsspecSourceConnector(SourceConnectorCleanupMixin, BaseSourceConnector):
    """Objects of this class support fetching document(s) from"""

    connector_config: SimpleFsspecConfig
    ingest_doc_cls: t.Type[FsspecIngestDoc] = FsspecIngestDoc

    def initialize(self):
        from fsspec import AbstractFileSystem, get_filesystem_class

        self.fs: AbstractFileSystem = get_filesystem_class(self.connector_config.protocol)(
            **self.connector_config.get_access_kwargs(),
        )

        """Verify that can get metadata for an object, validates connections info."""
        ls_output = self.fs.ls(self.connector_config.path_without_protocol)
        if len(ls_output) < 1:
            raise ValueError(
                f"No objects found in {self.connector_config.path}.",
            )

    def _list_files(self):
        if not self.connector_config.recursive:
            # fs.ls does not walk directories
            # directories that are listed in cloud storage can cause problems
            # because they are seen as 0 byte files
            return [
                x.get("name")
                for x in self.fs.ls(self.connector_config.path_without_protocol, detail=True)
                if x.get("size") > 0
            ]
        else:
            # fs.find will recursively walk directories
            # "size" is a common key for all the cloud protocols with fs
            return [
                k
                for k, v in self.fs.find(
                    self.connector_config.path_without_protocol,
                    detail=True,
                ).items()
                if v.get("size") > 0
            ]

    def get_ingest_docs(self):
        return [
            self.ingest_doc_cls(
                read_config=self.read_config,
                connector_config=self.connector_config,
                partition_config=self.partition_config,
                remote_file_path=file,
            )
            for file in self._list_files()
        ]


@dataclass
class FsspecDestinationConnector(BaseDestinationConnector):
    connector_config: SimpleFsspecConfig

    def initialize(self):
        from fsspec import AbstractFileSystem, get_filesystem_class

        self.fs: AbstractFileSystem = get_filesystem_class(self.connector_config.protocol)(
            **self.connector_config.get_access_kwargs(),
        )

    def write(self, docs: t.List[BaseIngestDoc]) -> None:
        from fsspec import AbstractFileSystem, get_filesystem_class

        fs: AbstractFileSystem = get_filesystem_class(self.connector_config.protocol)(
            **self.connector_config.get_access_kwargs(),
        )

        logger.info(f"Writing content using filesystem: {type(fs).__name__}")

        for doc in docs:
            s3_file_path = str(doc._output_filename).replace(
                doc.partition_config.output_dir,
                self.connector_config.path,
            )
            s3_folder = self.connector_config.path
            if s3_folder[-1] != "/":
                s3_folder = f"{s3_file_path}/"
            if s3_file_path[0] == "/":
                s3_file_path = s3_file_path[1:]

            s3_output_path = s3_folder + s3_file_path
            logger.debug(f"Uploading {doc._output_filename} -> {s3_output_path}")
            fs.put_file(lpath=doc._output_filename, rpath=s3_output_path)
