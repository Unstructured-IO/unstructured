import hashlib
import logging
import typing as t

from unstructured.ingest.interfaces import PartitionConfig, ReadConfig
from unstructured.ingest.logger import ingest_log_streaming_init, logger
from unstructured.ingest.processor import process_documents
from unstructured.ingest.runner.utils import update_download_dir_hash
from unstructured.ingest.runner.writers import writer_map


def jira(
    verbose: bool,
    read_config: ReadConfig,
    partition_config: PartitionConfig,
    url: str,
    user_email: str,
    api_token: str,
    projects: t.Optional[t.List[str]],
    boards: t.Optional[t.List[str]],
    issues: t.Optional[t.List[str]],
    writer_type: t.Optional[str] = None,
    writer_kwargs: t.Optional[dict] = None,
    **kwargs,
):
    writer_kwargs = writer_kwargs if writer_kwargs else {}

    projects = projects if projects else []
    boards = boards if boards else []
    issues = issues if issues else []
    ingest_log_streaming_init(logging.DEBUG if verbose else logging.INFO)

    hashed_dir_name = hashlib.sha256(
        url.encode("utf-8"),
    )

    read_config.download_dir = update_download_dir_hash(
        connector_name="jira",
        read_config=read_config,
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
        read_config=read_config,
        partition_config=partition_config,
    )

    dest_doc_connector = None
    if writer_type:
        writer = writer_map[writer_type]
        dest_doc_connector = writer(**writer_kwargs)

    process_documents(
        source_doc_connector=source_doc_connector,
        partition_config=partition_config,
        verbose=verbose,
        dest_doc_connector=dest_doc_connector,
    )
