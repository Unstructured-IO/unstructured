import hashlib
import logging
import typing as t

from unstructured.ingest.interfaces import PartitionConfig, ReadConfig
from unstructured.ingest.logger import ingest_log_streaming_init, logger
from unstructured.ingest.processor import process_documents
from unstructured.ingest.runner.utils import update_download_dir_hash
from unstructured.ingest.runner.writers import writer_map


def reddit(
    verbose: bool,
    read_config: ReadConfig,
    partition_config: PartitionConfig,
    subreddit_name: str,
    client_id: t.Optional[str],
    client_secret: t.Optional[str],
    user_agent: str,
    search_query: t.Optional[str],
    num_posts: int,
    writer_type: t.Optional[str] = None,
    writer_kwargs: t.Optional[dict] = None,
    **kwargs,
):
    writer_kwargs = writer_kwargs if writer_kwargs else {}

    ingest_log_streaming_init(logging.DEBUG if verbose else logging.INFO)

    hashed_dir_name = hashlib.sha256(
        subreddit_name.encode("utf-8"),
    )

    read_config.download_dir = update_download_dir_hash(
        connector_name="reddit",
        read_config=read_config,
        hashed_dir_name=hashed_dir_name,
        logger=logger,
    )

    from unstructured.ingest.connector.reddit import (
        RedditSourceConnector,
        SimpleRedditConfig,
    )

    source_doc_connector = RedditSourceConnector(  # type: ignore
        connector_config=SimpleRedditConfig(
            subreddit_name=subreddit_name,
            client_id=client_id,
            client_secret=client_secret,
            user_agent=user_agent,
            search_query=search_query,
            num_posts=num_posts,
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
