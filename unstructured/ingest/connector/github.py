import fnmatch
import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Optional
from urllib.parse import urlparse

import requests

from unstructured.ingest.interfaces import (
    BaseConnector,
    BaseConnectorConfig,
    BaseIngestDoc,
)
from unstructured.utils import requires_dependencies

if TYPE_CHECKING:
    from github.Repository import Repository


@dataclass
class SimpleGitHubConfig(BaseConnectorConfig):
    github_url: str
    github_access_token: Optional[str]
    github_branch: Optional[str]
    github_file_glob: Optional[str]

    # Standard Connector options
    download_dir: str
    # where to write structured data, with the directory structure matching the github repository
    output_dir: str
    preserve_downloads: bool = False
    re_download: bool = False
    verbose: bool = False

    repo_owner: str = field(init=False, repr=False)
    repo_name: str = field(init=False, repr=False)

    def __post_init__(self):
        parsed_gh_url = urlparse(self.github_url)
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
        self.repo_owner = path_fragments[0]
        self.repo_name = path_fragments[1]


@dataclass
class GitHubIngestDoc(BaseIngestDoc):
    config: SimpleGitHubConfig = field(repr=False)
    repo: "Repository"
    path: str

    @property
    def filename(self):
        return (Path(self.config.download_dir) / self.path).resolve()

    def _output_filename(self):
        return Path(self.config.output_dir) / f"{self.path}.json"

    def _create_full_tmp_dir_path(self):
        """includes directories in in the github repository"""
        self.filename.parent.mkdir(parents=True, exist_ok=True)

    def cleanup_file(self):
        """Removes the local copy the file (or anything else) after successful processing."""
        if not self.config.preserve_downloads:
            if self.config.verbose:
                print(f"cleaning up {self}")
            os.unlink(self.filename)

    def get_file(self):
        """Fetches the "remote" doc and stores it locally on the filesystem."""
        self._create_full_tmp_dir_path()
        if not self.config.re_download and self.filename.is_file() and self.filename.stat():
            if self.config.verbose:
                print(f"File exists: {self.filename}, skipping download")
            return

        if self.config.verbose:
            print(f"fetching {self} - PID: {os.getpid()}")
        content_file = self.repo.get_contents(self.path)
        contents = b""
        if (
            not content_file.content  # type: ignore
            and content_file.encoding == "none"  # type: ignore
            and content_file.size  # type: ignore
        ):
            print("File too large for the GitHub API, using direct download link instead.")
            response = requests.get(content_file.download_url)  # type: ignore
            if response.status_code != 200:
                print("Direct download link has failed... Skipping this file.")
            else:
                contents = response.content
        else:
            contents = content_file.decoded_content  # type: ignore

        with open(self.filename, "wb") as f:
            f.write(contents)

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
        print(f"Wrote {output_filename}")


@requires_dependencies(["github"], extras="github")
class GitHubConnector(BaseConnector):
    def __init__(self, config: SimpleGitHubConfig):
        from github import Github

        self.config = config
        self.github = Github(self.config.github_access_token)
        self.cleanup_files = not config.preserve_downloads

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
        if not supported and self.config.verbose:
            print(f"The file {path!r} is discarded as it does not contain a supported filetype.")
        return supported

    def does_path_match_glob(self, path: str) -> bool:
        if not self.config.github_file_glob:
            return True
        patterns = self.config.github_file_glob.split(",")
        for pattern in patterns:
            if fnmatch.filter([path], pattern):
                return True
        if self.config.verbose:
            print(f"The file {path!r} is discarded as it does not match any given glob.")
        return False

    def get_ingest_docs(self):
        repo = self.github.get_repo(f"{self.config.repo_owner}/{self.config.repo_name}")

        # Load the Git tree with all files, and then create Ingest docs
        # for all blobs, i.e. all files, ignoring directories
        sha = self.config.github_branch or repo.default_branch
        git_tree = repo.get_git_tree(sha, recursive=True)
        return [
            GitHubIngestDoc(self.config, repo, element.path)
            for element in git_tree.tree
            if element.type == "blob"
            and self.is_file_type_supported(element.path)
            and (not self.config.github_file_glob or self.does_path_match_glob(element.path))
        ]
