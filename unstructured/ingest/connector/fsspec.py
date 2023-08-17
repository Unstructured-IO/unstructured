import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Type

from unstructured.ingest.interfaces import (
    BaseConnector,
    BaseConnectorConfig,
    BaseIngestDoc,
    ConnectorCleanupMixin,
    IngestDocCleanupMixin,
    StandardConnectorConfig,
)
from unstructured.ingest.logger import logger

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


@dataclass(frozen=True)
class SimpleFsspecConfig(BaseConnectorConfig):
    # fsspec specific options
    path: str
    recursive: bool
    access_kwargs: dict = field(default_factory=dict)

    @property
    def protocol(self):
        return self.path.split("://")[0]
    
    @property
    def path_without_protocol(self):
        return self.path.split("://")[1]
   
    @property
    def dir_path(self):
        if self.protocol == "dropbox":
            return " "
        match = re.match(rf"{self.protocol}://([^/\s]+?)(/*)$", self.path)
        if match:
            return match.group(1)        
        match = re.match(rf"{self.protocol}://([^/\s]+?)/([^\s]*)", self.path)
        if not match:
            raise ValueError(f"Invalid path {self.path}.")
        return match.group(1)

    @property
    def file_path(self):
        if self.protocol == "dropbox":
            return ""
        match = re.match(rf"{self.protocol}://([^/\s]+?)(/*)$", self.path)
        if match:
            return ""
        match = re.match(rf"{self.protocol}://([^/\s]+?)/([^\s]*)", self.path)
        if not match:
            raise ValueError(f"Invalid path {self.path}.")
        return match.group(2) or ""
        
    def __post_init__(self):
        if self.protocol not in SUPPORTED_REMOTE_FSSPEC_PROTOCOLS:
            raise ValueError(
                f"Protocol {self.protocol} not supported yet, only "
                f"{SUPPORTED_REMOTE_FSSPEC_PROTOCOLS} are supported.",
            )

@dataclass
class FsspecIngestDoc(IngestDocCleanupMixin, BaseIngestDoc):
    """Class encapsulating fetching a doc and writing processed results (but not
    doing the processing!).

    Also includes a cleanup method. When things go wrong and the cleanup
    method is not called, the file is left behind on the filesystem to assist debugging.
    """

    config: SimpleFsspecConfig
    remote_file_path: str

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
        from fsspec import AbstractFileSystem, get_filesystem_class

        self._create_full_tmp_dir_path()
        fs: AbstractFileSystem = get_filesystem_class(self.config.protocol)(
            **self.config.access_kwargs,
        )
        logger.debug(f"Fetching {self} - PID: {os.getpid()}")
        fs.get(rpath=self.remote_file_path, lpath=self._tmp_download_file().as_posix())

    @property
    def filename(self):
        """The filename of the file after downloading from cloud"""
        return self._tmp_download_file()


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
        self.fs: AbstractFileSystem = get_filesystem_class(self.config.protocol)(
            **self.config.access_kwargs,
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
            )
            for file in self._list_files()
        ]
