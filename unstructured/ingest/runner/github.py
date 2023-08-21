import hashlib
import logging
from typing import Optional

from unstructured.ingest.interfaces import ProcessorConfigs, StandardConnectorConfig
from unstructured.ingest.logger import ingest_log_streaming_init, logger
from unstructured.ingest.processor import process_documents
from unstructured.ingest.runner.utils import update_download_dir_hash


def github(
    verbose: bool,
    connector_config: StandardConnectorConfig,
    processor_config: ProcessorConfigs,
    url: str,
    git_branch: str,
    git_access_token: Optional[str],
    git_file_glob: Optional[str],
    **kwargs,
):
    ingest_log_streaming_init(logging.DEBUG if verbose else logging.INFO)

    hashed_dir_name = hashlib.sha256(
        f"{url}_{git_branch}".encode(
            "utf-8",
        ),
    )
    connector_config.download_dir = update_download_dir_hash(
        connector_name="github",
        connector_config=connector_config,
        hashed_dir_name=hashed_dir_name,
        logger=logger,
    )

    from unstructured.ingest.connector.github import (
        GitHubConnector,
        SimpleGitHubConfig,
    )

    doc_connector = GitHubConnector(  # type: ignore
        standard_config=connector_config,
        config=SimpleGitHubConfig(
            url=url,
            access_token=git_access_token,
            branch=git_branch,
            file_glob=git_file_glob,
        ),
    )

    process_documents(doc_connector=doc_connector, processor_config=processor_config)
