import hashlib
import logging
from typing import Optional

from unstructured.ingest.interfaces import ProcessorConfigs, StandardConnectorConfig
from unstructured.ingest.logger import ingest_log_streaming_init, logger
from unstructured.ingest.processor import process_documents
from unstructured.ingest.runner.utils import update_download_dir_hash


def jira(
    verbose: bool,
    connector_config: StandardConnectorConfig,
    processor_config: ProcessorConfigs,
    url: str,
    user_email: str,
    api_token: str,
    list_of_projects: Optional[str],
    list_of_boards: Optional[str],
    list_of_issues: Optional[str],
    **kwargs,
):
    ingest_log_streaming_init(logging.DEBUG if verbose else logging.INFO)

    hashed_dir_name = hashlib.sha256(
        url.encode("utf-8"),
    )
    connector_config.download_dir = update_download_dir_hash(
        connector_name="jira",
        connector_config=connector_config,
        hashed_dir_name=hashed_dir_name,
        logger=logger,
    )

    from unstructured.ingest.connector.jira import (
        JiraConnector,
        SimpleJiraConfig,
    )

    doc_connector = JiraConnector(  # type: ignore
        standard_config=connector_config,
        config=SimpleJiraConfig(
            url=url,
            user_email=user_email,
            api_token=api_token,
            list_of_projects=list_of_projects,
            list_of_boards=list_of_boards,
            list_of_issues=list_of_issues,
        ),
    )

    process_documents(doc_connector=doc_connector, processor_config=processor_config)
