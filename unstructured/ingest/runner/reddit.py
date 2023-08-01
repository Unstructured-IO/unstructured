import hashlib
import logging
from typing import Optional

from unstructured.ingest.interfaces import ProcessorConfigs, StandardConnectorConfig
from unstructured.ingest.logger import ingest_log_streaming_init, logger
from unstructured.ingest.processor import process_documents
from unstructured.ingest.runner.utils import update_download_dir_hash


def reddit(
    verbose: bool,
    connector_config: StandardConnectorConfig,
    processor_config: ProcessorConfigs,
    subreddit_name: str,
    client_id: Optional[str],
    client_secret: Optional[str],
    user_agent: str,
    search_query: Optional[str],
    num_posts: int,
    **kwargs,
):
    ingest_log_streaming_init(logging.DEBUG if verbose else logging.INFO)

    hashed_dir_name = hashlib.sha256(
        subreddit_name.encode("utf-8"),
    )
    connector_config.download_dir = update_download_dir_hash(
        connector_config=connector_config,
        hashed_dir_name=hashed_dir_name,
        logger=logger,
    )

    from unstructured.ingest.connector.reddit import (
        RedditConnector,
        SimpleRedditConfig,
    )

    doc_connector = RedditConnector(  # type: ignore
        standard_config=connector_config,
        config=SimpleRedditConfig(
            subreddit_name=subreddit_name,
            client_id=client_id,
            client_secret=client_secret,
            user_agent=user_agent,
            search_query=search_query,
            num_posts=num_posts,
        ),
    )

    process_documents(doc_connector=doc_connector, processor_config=processor_config)
