from dataclasses import dataclass
from typing import TYPE_CHECKING
from urllib.parse import urlparse

from unstructured.ingest.connector.git import (
    GitConnector,
    GitFileMeta,
    GitIngestDoc,
    SimpleGitConfig,
)
from unstructured.ingest.error import SourceConnectionError
from unstructured.utils import requires_dependencies

if TYPE_CHECKING:
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
    def _get_project(self) -> "Project":
        from gitlab import Gitlab

        gitlab = Gitlab(self.base_url, private_token=self.access_token)
        return gitlab.projects.get(self.repo_path)


@dataclass
class GitLabIngestDoc(GitIngestDoc):
    config: SimpleGitLabConfig
    registry_name: str = "gitlab"

    def _fetch_content(self):
        try:
            project = self.config._get_project()
            content_file = project.files.get(
                self.path,
                ref=self.config.branch or project.default_branch,
            )
        except Exception as e:
            self.file_exists = False
            raise
        self.file_exists = True
        return content_file

    def _fetch_and_write(self) -> None:
        content_file = self._fetch_content()
        contents = content_file.decode()
        self.file_exists = True
        self.get_file_metadata(content_file)
        with open(self.filename, "wb") as f:
            f.write(contents)

    def get_file_metadata(self, content_file=None):
        if content_file is None:
            content_file = self._fetch_content()
        self.file_metadata = GitFileMeta(
            None,
            None,
            content_file.attributes.get("commit_id", ""),
        )


@requires_dependencies(["gitlab"], extras="gitlab")
@dataclass
class GitLabConnector(GitConnector):
    config: SimpleGitLabConfig

    def get_ingest_docs(self):
        # Load the Git tree with all files, and then create Ingest docs
        # for all blobs, i.e. all files, ignoring directories
        project = self.config._get_project()
        ref = self.config.branch or project.default_branch
        git_tree = project.repository_tree(
            ref=ref,
            recursive=True,
            iterator=True,
            all=True,
        )
        return [
            GitLabIngestDoc(self.standard_config, self.config, element["path"])
            for element in git_tree
            if element["type"] == "blob"
            and self.is_file_type_supported(element["path"])
            and (not self.config.file_glob or self.does_path_match_glob(element["path"]))
        ]
