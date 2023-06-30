from dataclasses import dataclass
from typing import TYPE_CHECKING
from urllib.parse import urlparse

import requests

from unstructured.ingest.connector.git import (
    GitConnector,
    GitIngestDoc,
    SimpleGitConfig,
)
from unstructured.ingest.logger import logger
from unstructured.utils import requires_dependencies

if TYPE_CHECKING:
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


@dataclass
class GitHubIngestDoc(GitIngestDoc):
    repo: "Repository"

    def _fetch_and_write(self) -> None:
        content_file = self.repo.get_contents(self.path)
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
class GitHubConnector(GitConnector):
    def __post_init__(self) -> None:
        from github import Github

        self.github = Github(self.config.access_token)

    def get_ingest_docs(self):
        repo = self.github.get_repo(self.config.repo_path)

        # Load the Git tree with all files, and then create Ingest docs
        # for all blobs, i.e. all files, ignoring directories
        sha = self.config.branch or repo.default_branch
        git_tree = repo.get_git_tree(sha, recursive=True)
        return [
            GitHubIngestDoc(self.standard_config, self.config, element.path, repo)
            for element in git_tree.tree
            if element.type == "blob"
            and self.is_file_type_supported(element.path)
            and (not self.config.file_glob or self.does_path_match_glob(element.path))
        ]
