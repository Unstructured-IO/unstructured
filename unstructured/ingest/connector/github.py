import typing as t
from dataclasses import dataclass
from urllib.parse import urlparse

import requests

from unstructured.ingest.connector.git import (
    GitIngestDoc,
    GitSourceConnector,
    SimpleGitConfig,
)
from unstructured.ingest.error import SourceConnectionError
from unstructured.ingest.logger import logger
from unstructured.utils import requires_dependencies

if t.TYPE_CHECKING:
    from github.Repository import Repository


@dataclass
class SimpleGitHubConfig(SimpleGitConfig):
    def __post_init__(self):
        parsed_gh_url = urlparse(self.url)
        path_fragments = [fragment for fragment in parsed_gh_url.path.split("/") if fragment]

        # If a scheme and netloc are provided, ensure they are correct
        # Additionally, ensure that the path contains two fragments
        if (
            (parsed_gh_url.scheme and parsed_gh_url.scheme != "https")
            or (parsed_gh_url.netloc and parsed_gh_url.netloc != "github.com")
            or len(path_fragments) != 2
        ):
            raise ValueError(
                'Please provide a valid URL, e.g. "https://github.com/Unstructured-IO/unstructured"'
                ' or a repository owner/name pair, e.g. "Unstructured-IO/unstructured".',
            )

        # If there's no issues, store the core repository info
        self.repo_path = parsed_gh_url.path

    @SourceConnectionError.wrap
    @requires_dependencies(["github"], extras="github")
    def get_repo(self) -> "Repository":
        from github import Github

        github = Github(self.access_token)
        return github.get_repo(self.repo_path)


@dataclass
class GitHubIngestDoc(GitIngestDoc):
    connector_config: SimpleGitHubConfig
    registry_name: str = "github"

    def _fetch_and_write(self) -> None:
        content_file = self.connector_config.get_repo().get_contents(self.path)
        contents = b""
        if (
            not content_file.content  # type: ignore
            and content_file.encoding == "none"  # type: ignore
            and content_file.size  # type: ignore
        ):
            logger.info("File too large for the GitHub API, using direct download link instead.")
            response = requests.get(content_file.download_url)  # type: ignore
            if response.status_code != 200:
                logger.info("Direct download link has failed... Skipping this file.")
            else:
                contents = response.content
        else:
            contents = content_file.decoded_content  # type: ignore

        with open(self.filename, "wb") as f:
            f.write(contents)


@requires_dependencies(["github"], extras="github")
@dataclass
class GitHubSourceConnector(GitSourceConnector):
    connector_config: SimpleGitHubConfig

    def get_ingest_docs(self):
        repo = self.connector_config.get_repo()
        # Load the Git tree with all files, and then create Ingest docs
        # for all blobs, i.e. all files, ignoring directories
        sha = self.connector_config.branch or repo.default_branch
        git_tree = repo.get_git_tree(sha, recursive=True)
        return [
            GitHubIngestDoc(
                connector_config=self.connector_config,
                partition_config=self.partition_config,
                read_config=self.read_config,
                path=element.path,
            )
            for element in git_tree.tree
            if element.type == "blob"
            and self.is_file_type_supported(element.path)
            and (not self.connector_config.file_glob or self.does_path_match_glob(element.path))
        ]
