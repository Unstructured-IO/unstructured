from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, Optional
from urllib.parse import urlparse

import requests

from unstructured.ingest.connector.git import (
    GitConnector,
    GitFileMeta,
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

    @requires_dependencies(["github"], extras="github")
    def _get_repo(self) -> "Repository":
        from github import Github

        github = Github(self.access_token)
        return github.get_repo(self.repo_path)


@dataclass
class GitHubIngestDoc(GitIngestDoc):
    config: SimpleGitHubConfig
    registry_name: str = "github"

    def _fetch_content(self, is_content_file=False):
        try:
            content_file = self.config._get_repo().get_contents(self.path)
            self.file_exists = True
        except Exception as e:
            logger.error(f"Couldn't retrieve file {self.path}")
            self.file_exists = False
            raise
        if is_content_file:
            return content_file

        contents = b""
        if (
            not content_file.content  # type: ignore
            and content_file.encoding == "none"  # type: ignore
            and content_file.size  # type: ignore
        ):
            logger.info("File too large for the GitHub API, using direct download link instead.")
            # NOTE: Maybe add a raise_for_status to catch connection timeout or HTTP Errors?
            response = requests.get(content_file.download_url)  # type: ignore
            if response.status_code != 200:
                self.file_exists = False
                logger.info("Direct download link has failed... Skipping this file.")
            else:
                contents = response.content
        else:
            contents = content_file.decoded_content  # type: ignore
        return contents

    def get_file_metadata(self):
        content_file = self.config._get_repo().get_contents(self.path)
        self.file_metadata = GitFileMeta(
            None,
            datetime.strptime(content_file.last_modified, "%a, %d %b %Y %H:%M:%S %Z").isoformat(),
            content_file.etag,
        )

    def _fetch_and_write(self) -> None:
        contents = self._fetch_content()
        self.get_file_metadata()
        with open(self.filename, "wb") as f:
            f.write(contents)


@requires_dependencies(["github"], extras="github")
@dataclass
class GitHubConnector(GitConnector):
    config: SimpleGitHubConfig

    def get_ingest_docs(self):
        from github.GithubException import UnknownObjectException

        try:
            repo = self.config._get_repo()
        except UnknownObjectException:
            logger.error(f"Repository {self.config.repo_path} does not exist.")
            return []
        # Load the Git tree with all files, and then create Ingest docs
        # for all blobs, i.e. all files, ignoring directories
        sha = self.config.branch or repo.default_branch
        git_tree = repo.get_git_tree(sha, recursive=True)
        return [
            GitHubIngestDoc(self.standard_config, self.config, element.path)
            for element in git_tree.tree
            if element.type == "blob"
            and self.is_file_type_supported(element.path)
            and (not self.config.file_glob or self.does_path_match_glob(element.path))
        ]
