from dataclasses import dataclass
from typing import TYPE_CHECKING
from urllib.parse import urlparse

from unstructured.ingest.connector.git import (
    GitConnector,
    GitIngestDoc,
    SimpleGitConfig,
)
from unstructured.utils import requires_dependencies

if TYPE_CHECKING:
    from gitlab.v4.objects.projects import Project


@dataclass(frozen=True)
class SimpleGitLabConfig(SimpleGitConfig):

    @property
    def parsed_gh_url(self):
        return urlparse(self.url)
    
    @property
    def repo_path(self):
        repo_path = self.parsed_gh_url.path
        while repo_path.startswith("/"):
            repo_path = repo_path[1:]
        return repo_path
    
    @property
    def url_with_scheme(self):
        # If no scheme or netloc are provided, use the default gitlab.com
        if not self.parsed_gh_url.scheme and not self.parsed_gh_url.netloc:
            return "https://gitlab.com"
        else:
            return f"{self.parsed_gh_url.scheme}://{self.parsed_gh_url.netloc}"

@dataclass
class GitLabIngestDoc(GitIngestDoc):
    project: "Project"

    def _fetch_and_write(self) -> None:
        content_file = self.project.files.get(
            self.path,
            ref=self.config.branch or self.project.default_branch,
        )
        contents = content_file.decode()

        with open(self.filename, "wb") as f:
            f.write(contents)


@requires_dependencies(["gitlab"], extras="gitlab")
@dataclass
class GitLabConnector(GitConnector):
    def __post_init__(self) -> None:
        from gitlab import Gitlab

        self.gitlab = Gitlab(self.config.url_with_scheme, private_token=self.config.access_token)

    def get_ingest_docs(self):
        # Load the Git tree with all files, and then create Ingest docs
        # for all blobs, i.e. all files, ignoring directories
        project = self.gitlab.projects.get(self.config.repo_path)
        ref = self.config.branch or project.default_branch
        git_tree = project.repository_tree(
            ref=ref,
            recursive=True,
            iterator=True,
            all=True,
        )
        return [
            GitLabIngestDoc(self.standard_config, self.config, element["path"], project)
            for element in git_tree
            if element["type"] == "blob"
            and self.is_file_type_supported(element["path"])
            and (not self.config.file_glob or self.does_path_match_glob(element["path"]))
        ]
