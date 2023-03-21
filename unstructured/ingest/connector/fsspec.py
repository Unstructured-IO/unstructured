import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Type

from unstructured.ingest.interfaces import (
    BaseConnector,
    BaseConnectorConfig,
    BaseIngestDoc,
)
from unstructured.ingest.logger import logger

SUPPORTED_REMOTE_FSSPEC_PROTOCOLS = [
    "s3",
    "abfs",
    "az",
]


@dataclass
class SimpleFsspecConfig(BaseConnectorConfig):
    # fsspec specific options
    path: str

    # base connector options
    download_dir: str
    output_dir: str
    preserve_downloads: bool = False
    re_download: bool = False
    metadata_include: Optional[str] = None
    metadata_exclude: Optional[str] = None

    # fsspec specific options
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
class FsspecIngestDoc(BaseIngestDoc):
    """Class encapsulating fetching a doc and writing processed results (but not
    doing the processing!).

    Also includes a cleanup method. When things go wrong and the cleanup
    method is not called, the file is left behind on the filesystem to assist debugging.
    """

    config: SimpleFsspecConfig
    remote_file_path: str

    def _tmp_download_file(self):
        return Path(self.config.download_dir) / self.remote_file_path.replace(
            f"{self.config.dir_path}/",
            "",
        )

    def _output_filename(self):
        return (
            Path(self.config.output_dir)
            / f"{self.remote_file_path.replace(f'{self.config.dir_path}/', '')}.json"
        )

    def has_output(self):
        """Determine if structured output for this doc already exists."""
        return self._output_filename().is_file() and os.path.getsize(self._output_filename())

    def _create_full_tmp_dir_path(self):
        """Includes "directories" in the object path"""
        self._tmp_download_file().parent.mkdir(parents=True, exist_ok=True)

    def get_file(self):
        """Fetches the file from the current filesystem and stores it locally."""
        from fsspec import AbstractFileSystem, get_filesystem_class

        self._create_full_tmp_dir_path()
        if (
            not self.config.re_download
            and self._tmp_download_file().is_file()
            and os.path.getsize(self._tmp_download_file())
        ):
            logger.debug(f"File exists: {self._tmp_download_file()}, skipping download")
            return

        fs: AbstractFileSystem = get_filesystem_class(self.config.protocol)(
            **self.config.access_kwargs,
        )

        logger.debug(f"Fetching {self} - PID: {os.getpid()}")
        fs.get(rpath=self.remote_file_path, lpath=self._tmp_download_file().as_posix())

    def write_result(self):
        """Write the structured json result for this doc. result must be json serializable."""
        output_filename = self._output_filename()
        output_filename.parent.mkdir(parents=True, exist_ok=True)
        with open(output_filename, "w") as output_f:
            output_f.write(json.dumps(self.isd_elems_no_filename, ensure_ascii=False, indent=2))
        logger.info(f"Wrote {output_filename}")

    @property
    def filename(self):
        """The filename of the file after downloading from s3"""
        return self._tmp_download_file()

    def cleanup_file(self):
        """Removes the local copy the file after successful processing."""
        if not self.config.preserve_downloads:
            logger.debug(f"Cleaning up {self}")
            os.unlink(self._tmp_download_file())


class FsspecConnector(BaseConnector):
    """Objects of this class support fetching document(s) from"""

    ingest_doc_cls: Type[FsspecIngestDoc] = FsspecIngestDoc

    def __init__(
        self,
        config: SimpleFsspecConfig,
    ):
        from fsspec import AbstractFileSystem, get_filesystem_class

        self.config = config
        self.fs: AbstractFileSystem = get_filesystem_class(self.config.protocol)(
            **self.config.access_kwargs,
        )
        self.cleanup_files = not config.preserve_downloads

    def cleanup(self, cur_dir=None):
        """cleanup linginering empty sub-dirs from s3 paths, but leave remaining files
        (and their paths) in tact as that indicates they were not processed"""
        if not self.cleanup_files:
            return

        if cur_dir is None:
            cur_dir = self.config.download_dir
        sub_dirs = os.listdir(cur_dir)
        os.chdir(cur_dir)
        for sub_dir in sub_dirs:
            # don't traverse symlinks, not that there every should be any
            if os.path.isdir(sub_dir) and not os.path.islink(sub_dir):
                self.cleanup(sub_dir)
        os.chdir("..")
        if len(os.listdir(cur_dir)) == 0:
            os.rmdir(cur_dir)

    def initialize(self):
        """Verify that can get metadata for an object, validates connections info."""
        ls_output = self.fs.ls(self.config.path_without_protocol)
        if len(ls_output) < 1:
            raise ValueError(
                f"No objects found in {self.config.path}.",
            )

    def _list_files(self):
        return self.fs.ls(self.config.path_without_protocol)

    def get_ingest_docs(self):
        return [
            self.ingest_doc_cls(
                self.config,
                file,
            )
            for file in self._list_files()
        ]
