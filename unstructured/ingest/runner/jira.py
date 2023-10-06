import hashlib
import logging
import typing as t

from unstructured.ingest.logger import ingest_log_streaming_init, logger
from unstructured.ingest.runner.base_runner import Runner
from unstructured.ingest.runner.utils import update_download_dir_hash


class JiraRunner(Runner):
    def run(
        self,
        url: str,
        user_email: str,
        api_token: str,
        projects: t.Optional[t.List[str]] = None,
        boards: t.Optional[t.List[str]] = None,
        issues: t.Optional[t.List[str]] = None,
        **kwargs,
    ):
        projects = projects if projects else []
        boards = boards if boards else []
        issues = issues if issues else []
        ingest_log_streaming_init(logging.DEBUG if self.processor_config.verbose else logging.INFO)

        hashed_dir_name = hashlib.sha256(
            url.encode("utf-8"),
        )

        self.read_config.download_dir = update_download_dir_hash(
            connector_name="jira",
            read_config=self.read_config,
            hashed_dir_name=hashed_dir_name,
            logger=logger,
        )

        from unstructured.ingest.connector.jira import (
            JiraSourceConnector,
            SimpleJiraConfig,
        )

        source_doc_connector = JiraSourceConnector(  # type: ignore
            connector_config=SimpleJiraConfig(
                url=url,
                user_email=user_email,
                api_token=api_token,
                projects=projects,
                boards=boards,
                issues=issues,
            ),
            read_config=self.read_config,
            processor_config=self.processor_config,
        )

        self.process_documents(source_doc_connector=source_doc_connector)
