import typing as t
from dataclasses import dataclass
from urllib.parse import urlparse

from unstructured.ingest.connector.git import (
    GitIngestDoc,
    GitSourceConnector,
    SimpleGitConfig,
)
from unstructured.ingest.error import SourceConnectionError
from unstructured.ingest.interfaces import SourceMetadata
from unstructured.ingest.logger import logger
from unstructured.utils import requires_dependencies

if t.TYPE_CHECKING:
    from gitlab.v4.objects.projects import Project


@dataclass
class SimpleGitLabConfig(SimpleGitConfig):
    base_url: str = "https://gitlab.com"

    def __post_init__(self):
        parsed_gh_url = urlparse(self.url)
        # If a scheme or netloc are provided, use the parsed base url
        if parsed_gh_url.scheme or parsed_gh_url.netloc:
            self.base_url = f"{parsed_gh_url.scheme}://{parsed_gh_url.netloc}"
        self.repo_path = parsed_gh_url.path
        while self.repo_path.startswith("/"):
            self.repo_path = self.repo_path[1:]

    @SourceConnectionError.wrap
    @requires_dependencies(["gitlab"], extras="gitlab")
    def get_project(self) -> "Project":
        from gitlab import Gitlab

        gitlab = Gitlab(self.base_url, private_token=self.access_token)
        return gitlab.projects.get(self.repo_path)


@dataclass
class GitLabIngestDoc(GitIngestDoc):
    connector_config: SimpleGitLabConfig
    registry_name: str = "gitlab"

    @property
    def date_created(self) -> t.Optional[str]:
        return None

    @property
    def date_modified(self) -> t.Optional[str]:
        return None

    @property
    def source_url(self) -> t.Optional[str]:
        return None

    @requires_dependencies(["gitlab"], extras="gitlab")
    def _fetch_content(self):
        from gitlab.exceptions import GitlabHttpError

        try:
            project = self.connector_config.get_project()
            content_file = project.files.get(
                self.path,
                ref=self.connector_config.branch or project.default_branch,
            )
        except GitlabHttpError as e:
            if e.response_code == 404:
                logger.error(f"File doesn't exists {self.connector_config.url}/{self.path}")
                return None
            raise
        return content_file

    def update_source_metadata(self, **kwargs):
        content_file = kwargs.get("content_file", self._fetch_content())
        if content_file is None:
            self.source_metadata = SourceMetadata(
                exists=None,
            )
            return
        self.source_metadata = SourceMetadata(
            version=content_file.attributes.get("last_commit_id", ""),
            exists=True,
        )

    def _fetch_and_write(self) -> None:
        content_file = self._fetch_content()
        self.update_source_metadata(content_file=content_file)
        if content_file is None:
            raise ValueError(
                f"Failed to retrieve file from repo "
                f"{self.connector_config.url}/{self.path}. Check logs.",
            )
        contents = content_file.decode()
        with open(self.filename, "wb") as f:
            f.write(contents)


@requires_dependencies(["gitlab"], extras="gitlab")
@dataclass
class GitLabSourceConnector(GitSourceConnector):
    connector_config: SimpleGitLabConfig

    def get_ingest_docs(self):
        # Load the Git tree with all files, and then create Ingest docs
        # for all blobs, i.e. all files, ignoring directories
        project = self.connector_config.get_project()
        ref = self.connector_config.branch or project.default_branch
        git_tree = project.repository_tree(
            ref=ref,
            recursive=True,
            iterator=True,
            all=True,
        )
        return [
            GitLabIngestDoc(
                connector_config=self.connector_config,
                processor_config=self.processor_config,
                read_config=self.read_config,
                path=element["path"],
            )
            for element in git_tree
            if element["type"] == "blob"
            and self.is_file_type_supported(element["path"])
            and (not self.connector_config.file_glob or self.does_path_match_glob(element["path"]))
        ]
