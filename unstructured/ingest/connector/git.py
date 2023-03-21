import fnmatch
import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from unstructured.ingest.interfaces import (
    BaseConnector,
    BaseConnectorConfig,
    BaseIngestDoc,
)
from unstructured.ingest.logger import logger


@dataclass
class SimpleGitConfig(BaseConnectorConfig):
    url: str
    access_token: Optional[str]
    branch: Optional[str]
    file_glob: Optional[str]

    # Standard Connector options
    download_dir: str
    # where to write structured data, with the directory structure matching the github repository
    output_dir: str
    preserve_downloads: bool = False
    re_download: bool = False
    metadata_include: Optional[str] = None
    metadata_exclude: Optional[str] = None

    repo_path: str = field(init=False, repr=False)


@dataclass
class GitIngestDoc(BaseIngestDoc):
    config: SimpleGitConfig = field(repr=False)
    path: str

    @property
    def filename(self):
        return (Path(self.config.download_dir) / self.path).resolve()

    def _output_filename(self):
        return Path(self.config.output_dir) / f"{self.path}.json"

    def _create_full_tmp_dir_path(self):
        """includes directories in in the gitlab repository"""
        self.filename.parent.mkdir(parents=True, exist_ok=True)

    def cleanup_file(self):
        """Removes the local copy the file (or anything else) after successful processing."""
        if not self.config.preserve_downloads:
            logger.debug(f"Cleaning up {self}")
            os.unlink(self.filename)

    def get_file(self):
        """Fetches the "remote" doc and stores it locally on the filesystem."""
        self._create_full_tmp_dir_path()
        if not self.config.re_download and self.filename.is_file() and self.filename.stat():
            logger.debug(f"File exists: {self.filename}, skipping download")
            return

        logger.debug(f"Fetching {self} - PID: {os.getpid()}")
        self._fetch_and_write()

    def _fetch_and_write(self) -> None:
        raise NotImplementedError()

    def has_output(self):
        """Determine if structured output for this doc already exists."""
        output_filename = self._output_filename()
        return output_filename.is_file() and output_filename.stat()

    def write_result(self):
        """Write the structured json result for this doc. result must be json serializable."""
        output_filename = self._output_filename()
        output_filename.parent.mkdir(parents=True, exist_ok=True)
        with open(output_filename, "w", encoding="utf8") as output_f:
            json.dump(self.isd_elems_no_filename, output_f, ensure_ascii=False, indent=2)
        logger.info(f"Wrote {output_filename}")


@dataclass
class GitConnector(BaseConnector):
    config: SimpleGitConfig

    def __post_init__(self) -> None:
        self.cleanup_files = not self.config.preserve_downloads

    def cleanup(self, cur_dir=None):
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
        pass

    def is_file_type_supported(self, path: str) -> bool:
        # Workaround to ensure that auto.partition isn't fed with .yaml, .py, etc. files
        # TODO: What to do with no filenames? e.g. LICENSE, Makefile, etc.
        supported = path.endswith(
            (
                ".md",
                ".txt",
                ".pdf",
                ".doc",
                ".docx",
                ".eml",
                ".html",
                ".png",
                ".jpg",
                ".ppt",
                ".pptx",
                ".xml",
            ),
        )
        if not supported:
            logger.debug(
                f"The file {path!r} is discarded as it does not contain a supported filetype.",
            )
        return supported

    def does_path_match_glob(self, path: str) -> bool:
        if not self.config.file_glob:
            return True
        patterns = self.config.file_glob.split(",")
        for pattern in patterns:
            if fnmatch.filter([path], pattern):
                return True
        logger.debug(f"The file {path!r} is discarded as it does not match any given glob.")
        return False
