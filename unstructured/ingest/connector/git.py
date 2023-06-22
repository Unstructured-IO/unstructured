import fnmatch
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from unstructured.ingest.interfaces import (
    BaseConnector,
    BaseConnectorConfig,
    BaseIngestDoc,
    ConnectorCleanupMixin,
    IngestDocCleanupMixin,
)
from unstructured.ingest.logger import logger


@dataclass
class SimpleGitConfig(BaseConnectorConfig):
    url: str
    access_token: Optional[str]
    branch: Optional[str]
    file_glob: Optional[str]
    repo_path: str = field(init=False, repr=False)


@dataclass
class GitIngestDoc(IngestDocCleanupMixin, BaseIngestDoc):
    config: SimpleGitConfig = field(repr=False)
    path: str

    @property
    def filename(self):
        return (Path(self.standard_config.download_dir) / self.path).resolve()

    @property
    def _output_filename(self):
        return Path(self.standard_config.output_dir) / f"{self.path}.json"

    def _create_full_tmp_dir_path(self):
        """includes directories in in the gitlab repository"""
        self.filename.parent.mkdir(parents=True, exist_ok=True)

    @BaseIngestDoc.skip_if_file_exists
    def get_file(self):
        """Fetches the "remote" doc and stores it locally on the filesystem."""
        self._create_full_tmp_dir_path()
        logger.debug(f"Fetching {self} - PID: {os.getpid()}")
        self._fetch_and_write()

    def _fetch_and_write(self) -> None:
        raise NotImplementedError()


@dataclass
class GitConnector(ConnectorCleanupMixin, BaseConnector):
    config: SimpleGitConfig

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
