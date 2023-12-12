import fnmatch
import typing as t
from dataclasses import dataclass, field
from pathlib import Path

from unstructured.ingest.enhanced_dataclass import enhanced_field
from unstructured.ingest.error import SourceConnectionError
from unstructured.ingest.interfaces import (
    AccessConfig,
    BaseConnectorConfig,
    BaseSingleIngestDoc,
    BaseSourceConnector,
    IngestDocCleanupMixin,
    SourceConnectorCleanupMixin,
)
from unstructured.ingest.logger import logger


@dataclass
class GitAccessConfig(AccessConfig):
    access_token: t.Optional[str] = enhanced_field(
        default=None, sensitive=True, overload_name="git_access_token"
    )


@dataclass
class SimpleGitConfig(BaseConnectorConfig):
    url: str
    access_config: GitAccessConfig
    branch: t.Optional[str] = enhanced_field(default=None, overload_name="git_branch")
    file_glob: t.Optional[t.List[str]] = enhanced_field(default=None, overload_name="git_file_glob")
    repo_path: str = field(init=False, repr=False)


@dataclass
class GitIngestDoc(IngestDocCleanupMixin, BaseSingleIngestDoc):
    connector_config: SimpleGitConfig = field(repr=False)
    path: str

    @property
    def filename(self):
        return (Path(self.read_config.download_dir) / self.path).resolve()

    @property
    def _output_filename(self):
        return Path(self.processor_config.output_dir) / f"{self.path}.json"

    @property
    def record_locator(self) -> t.Dict[str, t.Any]:
        record_locator = {
            "repo_path": self.connector_config.repo_path,
            "file_path": self.path,
        }
        if self.connector_config.branch is not None:
            record_locator["branch"] = self.connector_config.branch
        return record_locator

    def _create_full_tmp_dir_path(self):
        """includes directories in in the gitlab repository"""
        self.filename.parent.mkdir(parents=True, exist_ok=True)

    def update_source_metadata(self, **kwargs):
        raise NotImplementedError()

    @SourceConnectionError.wrap
    @BaseSingleIngestDoc.skip_if_file_exists
    def get_file(self):
        """Fetches the "remote" doc and stores it locally on the filesystem."""
        self._create_full_tmp_dir_path()
        self._fetch_and_write()

    def _fetch_content(self) -> None:
        raise NotImplementedError()

    def _fetch_and_write(self) -> None:
        raise NotImplementedError()


@dataclass
class GitSourceConnector(SourceConnectorCleanupMixin, BaseSourceConnector):
    connector_config: SimpleGitConfig

    def initialize(self):
        pass

    def check_connection(self):
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
        if not self.connector_config.file_glob:
            return True
        patterns = self.connector_config.file_glob
        for pattern in patterns:
            if fnmatch.filter([path], pattern):
                return True
        logger.debug(f"The file {path!r} is discarded as it does not match any given glob.")
        return False
