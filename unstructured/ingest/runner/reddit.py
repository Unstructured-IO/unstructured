import hashlib
import logging
import typing as t

from unstructured.ingest.logger import ingest_log_streaming_init, logger
from unstructured.ingest.runner.base_runner import Runner
from unstructured.ingest.runner.utils import update_download_dir_hash


class RedditRunner(Runner):
    def run(
        self,
        subreddit_name: str,
        user_agent: str,
        num_posts: int,
        client_id: t.Optional[str] = None,
        client_secret: t.Optional[str] = None,
        search_query: t.Optional[str] = None,
        **kwargs,
    ):
        ingest_log_streaming_init(logging.DEBUG if self.processor_config.verbose else logging.INFO)

        hashed_dir_name = hashlib.sha256(
            subreddit_name.encode("utf-8"),
        )

        self.read_config.download_dir = update_download_dir_hash(
            connector_name="reddit",
            read_config=self.read_config,
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
            read_config=self.read_config,
            processor_config=self.processor_config,
        )

        self.process_documents(source_doc_connector=source_doc_connector)
