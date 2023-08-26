import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, Optional, Type

from unstructured.ingest.interfaces import (
    BaseConnector,
    BaseConnectorConfig,
    BaseIngestDoc,
    ConnectorCleanupMixin,
    IngestDocCleanupMixin,
    StandardConnectorConfig,
)
from unstructured.ingest.logger import logger

if TYPE_CHECKING:
    from fsspec import AbstractFileSystem


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
    recursive: bool
    access_kwargs: dict = field(default_factory=dict)
    protocol: str = field(init=False)
    path_without_protocol: str = field(init=False)
    dir_path: str = field(init=False)
    file_path: str = field(init=False)

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

    def get_access_kwargs(self) -> dict:
        print("TEST FSSPEC")
        return self.access_kwargs


@dataclass
class FsspecIngestDoc(IngestDocCleanupMixin, BaseIngestDoc):
    """Class encapsulating fetching a doc and writing processed results (but not
    doing the processing!).

    Also includes a cleanup method. When things go wrong and the cleanup
    method is not called, the file is left behind on the filesystem to assist debugging.
    """

    config: SimpleFsspecConfig
    remote_file_path: str
    fs: "AbstractFileSystem"

    def _tmp_download_file(self):
        return Path(self.standard_config.download_dir) / self.remote_file_path.replace(
            f"{self.config.dir_path}/",
            "",
        )

    @property
    def _output_filename(self):
        return (
            Path(self.standard_config.output_dir)
            / f"{self.remote_file_path.replace(f'{self.config.dir_path}/', '')}.json"
        )

    def _create_full_tmp_dir_path(self):
        """Includes "directories" in the object path"""
        self._tmp_download_file().parent.mkdir(parents=True, exist_ok=True)

    @BaseIngestDoc.skip_if_file_exists
    def get_file(self):
        """Fetches the file from the current filesystem and stores it locally."""

        self._create_full_tmp_dir_path()
        print(self.config.get_access_kwargs())
        print(type(self.config))
        print(self.__class__)
        fs: AbstractFileSystem = get_filesystem_class(self.config.protocol)(
            **self.config.get_access_kwargs(),
        )
        logger.debug(f"Fetching {self} - PID: {os.getpid()}")
        try:
            self.fs.get(rpath=self.remote_file_path, lpath=self._tmp_download_file().as_posix())
        except Exception as e:
            logger.error(e)
            return

    @property
    def filename(self):
        """The filename of the file after downloading from cloud"""
        return self._tmp_download_file()

    @property
    def date_created(self) -> Optional[str]:
        return self.fs.created(self.remote_file_path).isoformat()

    @property
    def date_modified(self) -> Optional[str]:
        return self.fs.modified(self.remote_file_path).isoformat()

    @property
    def exists(self) -> Optional[bool]:
        return self.fs.exists(self.remote_file_path)

    @property
    def record_locator(self) -> Optional[Dict[str, Any]]:
        """Returns the equivalent of ls in dict"""
        return self.fs.info(self.remote_file_path)

    @property
    def version(self) -> Optional[str]:
        return str(self.fs.checksum(self.remote_file_path))


class FsspecConnector(ConnectorCleanupMixin, BaseConnector):
    """Objects of this class support fetching document(s) from"""

    config: SimpleFsspecConfig
    ingest_doc_cls: Type[FsspecIngestDoc] = FsspecIngestDoc

    def __init__(
        self,
        standard_config: StandardConnectorConfig,
        config: SimpleFsspecConfig,
    ):
        from fsspec import AbstractFileSystem, get_filesystem_class

        super().__init__(standard_config, config)
        print(type(self.config))
        print(self.__class__)
        self.fs: AbstractFileSystem = get_filesystem_class(self.config.protocol)(
            **self.config.get_access_kwargs(),
        )

    def initialize(self):
        """Verify that can get metadata for an object, validates connections info."""
        ls_output = self.fs.ls(self.config.path_without_protocol)
        if len(ls_output) < 1:
            raise ValueError(
                f"No objects found in {self.config.path}.",
            )

    def _list_files(self):
        if not self.config.recursive:
            # fs.ls does not walk directories
            # directories that are listed in cloud storage can cause problems
            # because they are seen as 0 byte files
            return [
                x.get("name")
                for x in self.fs.ls(self.config.path_without_protocol, detail=True)
                if x.get("size") > 0
            ]
        else:
            # fs.find will recursively walk directories
            # "size" is a common key for all the cloud protocols with fs
            return [
                k
                for k, v in self.fs.find(
                    self.config.path_without_protocol,
                    detail=True,
                ).items()
                if v.get("size") > 0
            ]

    def get_ingest_docs(self):
        return [
            self.ingest_doc_cls(
                standard_config=self.standard_config,
                config=self.config,
                remote_file_path=file,
                fs=self.fs,
            )
            for file in self._list_files()
        ]
