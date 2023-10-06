import hashlib
import logging
import typing as t

from unstructured.ingest.logger import ingest_log_streaming_init, logger
from unstructured.ingest.runner.base_runner import Runner
from unstructured.ingest.runner.utils import update_download_dir_hash


class GithubRunner(Runner):
    def run(
        self,
        url: str,
        git_branch: str,
        git_access_token: t.Optional[str] = None,
        git_file_glob: t.Optional[str] = None,
        **kwargs,
    ):
        ingest_log_streaming_init(logging.DEBUG if self.processor_config.verbose else logging.INFO)

        hashed_dir_name = hashlib.sha256(
            f"{url}_{git_branch}".encode(
                "utf-8",
            ),
        )

        self.read_config.download_dir = update_download_dir_hash(
            connector_name="github",
            read_config=self.read_config,
            hashed_dir_name=hashed_dir_name,
            logger=logger,
        )

        from unstructured.ingest.connector.github import (
            GitHubSourceConnector,
            SimpleGitHubConfig,
        )

        source_doc_connector = GitHubSourceConnector(  # type: ignore
            connector_config=SimpleGitHubConfig(
                url=url,
                access_token=git_access_token,
                branch=git_branch,
                file_glob=git_file_glob,
            ),
            read_config=self.read_config,
            processor_config=self.processor_config,
        )

        self.process_documents(source_doc_connector=source_doc_connector)
