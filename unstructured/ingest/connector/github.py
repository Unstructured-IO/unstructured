from copy import deepcopy
from dataclasses import dataclass, field
import json
import os
from pathlib import Path
from typing import Any, Dict, TYPE_CHECKING, Optional

from github import Github
from github.ContentFile import ContentFile
from github.Repository import Repository
from urllib.parse import urlparse

from unstructured.ingest.interfaces import (
    BaseConnector,
    BaseConnectorConfig,
    BaseIngestDoc,
)


@dataclass
class SimpleGitHubConfig(BaseConnectorConfig):
    github_url: str
    github_access_token: Optional[str]
    github_branch: Optional[str]

    # Standard Connector options
    download_dir: str
    # where to write structured data, with the directory structure matching s3 path
    output_dir: str
    preserve_downloads: bool = False
    re_download: bool = False
    # if a structured output .json file already exists, do not reprocess an s3 file to overwrite it
    reprocess: bool = False
    verbose: bool = False

    repo_owner: str = field(init=False, repr=False)
    repo_name: str = field(init=False, repr=False)

    def __post_init__(self):
        parsed_gh_url = urlparse(self.github_url)
        path_fragments = [
            fragment for fragment in parsed_gh_url.path.split("/") if fragment
        ]

        # If a scheme and netloc are provided, ensure they are correct
        # Additionally, ensure that the path contains two fragments
        if (
            (parsed_gh_url.scheme and parsed_gh_url.scheme != "https")
            or (parsed_gh_url.netloc and parsed_gh_url.netloc != "github.com")
            or len(path_fragments) != 2
        ):
            raise ValueError(
                'Please provide a valid URL, e.g. "https://github.com/Unstructured-IO/unstructured"'
                ' or a repository owner/name pair, e.g. "Unstructured-IO/unstructured".'
            )

        # If there's no issues, store the core repository info
        self.repo_owner = path_fragments[0]
        self.repo_name = path_fragments[1]


@dataclass
class GitHubIngestDoc(BaseIngestDoc):
    config: SimpleGitHubConfig = field(repr=False)
    repo: Repository
    path: str

    @property
    def filename(self):
        return (Path(self.config.download_dir) / self.path).resolve()

    def _output_filename(self):
        return Path(self.config.output_dir) / f"{self.path}.json"

    def _create_full_tmp_dir_path(self):
        """includes "directories" in s3 object path"""
        self.filename.parent.mkdir(parents=True, exist_ok=True)

    def cleanup_file(self):
        """Removes the local copy the file (or anything else) after successful processing.
        Not relevant for GitHubIngestDoc."""
        if not self.config.preserve_downloads:
            if self.config.verbose:
                print(f"cleaning up {self}")
            os.unlink(self.filename)

    def get_file(self):
        """Fetches the "remote" doc and stores it locally on the filesystem."""
        self._create_full_tmp_dir_path()
        if (
            not self.config.re_download
            and self.filename.is_file()
            and self.filename.stat()
        ):
            if self.config.verbose:
                print(f"File exists: {self.filename}, skipping download")
            return

        if self.config.verbose:
            print(f"fetching {self} - PID: {os.getpid()}")
        content_file = self.repo.get_contents(self.path)
        with open(self.filename, "wb") as f:
            f.write(content_file.decoded_content)

    def has_output(self):
        """Determine if structured output for this doc already exists."""
        output_filename = self._output_filename()
        return output_filename.is_file() and output_filename.stat()

    def write_result(self):
        """Write the structured json result for this doc. result must be json serializable."""
        output_filename = self._output_filename()
        output_filename.parent.mkdir(parents=True, exist_ok=True)
        with open(output_filename, "w", encoding="utf8") as output_f:
            json.dump(
                self.isd_elems_no_filename, output_f, ensure_ascii=False, indent=2
            )
        print(f"Wrote {output_filename}")


class GitHubConnector(BaseConnector):
    def __init__(self, config: SimpleGitHubConfig):
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
            )
        )
        if not supported and self.config.verbose:
            print(f"The file {path!r} is discarded as it does not contain a supported filetype.")
        return supported

    def get_ingest_docs(self):
        repo = self.github.get_repo(f"{self.config.repo_owner}/{self.config.repo_name}")

        # Load the Git tree with all files, and then create Ingest docs
        # for all blobs, i.e. all files, ignoring directories
        sha = self.config.github_branch or repo.default_branch
        git_tree = repo.get_git_tree(sha, recursive=True)
        # TODO: path glob filtering here
        return [
            GitHubIngestDoc(self.config, deepcopy(repo), element.path)
            for element in git_tree.tree
            if element.type == "blob" and self.is_file_type_supported(element.path)
        ]
