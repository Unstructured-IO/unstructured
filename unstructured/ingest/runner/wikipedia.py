import hashlib
import logging

from unstructured.ingest.logger import ingest_log_streaming_init, logger
from unstructured.ingest.runner.base_runner import Runner
from unstructured.ingest.runner.utils import update_download_dir_hash


class WikipediaRunner(Runner):
    def run(
        self,
        page_title: str,
        auto_suggest: bool = False,
        **kwargs,
    ):
        ingest_log_streaming_init(logging.DEBUG if self.processor_config.verbose else logging.INFO)

        hashed_dir_name = hashlib.sha256(
            page_title.encode("utf-8"),
        )

        self.read_config.download_dir = update_download_dir_hash(
            connector_name="wikipedia",
            read_config=self.read_config,
            hashed_dir_name=hashed_dir_name,
            logger=logger,
        )

        from unstructured.ingest.connector.wikipedia import (
            SimpleWikipediaConfig,
            WikipediaSourceConnector,
        )

        source_doc_connector = WikipediaSourceConnector(  # type: ignore
            connector_config=SimpleWikipediaConfig(
                title=page_title,
                auto_suggest=auto_suggest,
            ),
            read_config=self.read_config,
            processor_config=self.processor_config,
        )

        self.process_documents(source_doc_connector=source_doc_connector)
