import hashlib
import logging
import typing as t

from unstructured.ingest.logger import ingest_log_streaming_init, logger
from unstructured.ingest.runner.base_runner import Runner
from unstructured.ingest.runner.utils import update_download_dir_hash

if t.TYPE_CHECKING:
    from unstructured.ingest.connector.notion.connector import SimpleNotionConfig


class NotionRunner(Runner):
    connector_config: "SimpleNotionConfig"

    def run(
        self,
        **kwargs,
    ):
        ingest_log_streaming_init(logging.DEBUG if self.processor_config.verbose else logging.INFO)
        if not self.connector_config.page_ids and not self.connector_config.database_ids:
            raise ValueError("no page ids nor database ids provided")

        if self.connector_config.page_ids and self.connector_config.database_ids:
            hashed_dir_name = hashlib.sha256(
                "{},{}".format(
                    ",".join(self.connector_config.page_ids),
                    ",".join(self.connector_config.database_ids),
                ).encode("utf-8"),
            )
        elif self.connector_config.page_ids:
            hashed_dir_name = hashlib.sha256(
                ",".join(self.connector_config.page_ids).encode("utf-8"),
            )
        elif self.connector_config.database_ids:
            hashed_dir_name = hashlib.sha256(
                ",".join(self.connector_config.database_ids).encode("utf-8"),
            )
        else:
            raise ValueError("could not create local cache directory name")

        self.read_config.download_dir = update_download_dir_hash(
            connector_name="notion",
            read_config=self.read_config,
            hashed_dir_name=hashed_dir_name,
            logger=logger,
        )

        from unstructured.ingest.connector.notion.connector import (
            NotionSourceConnector,
        )

        source_doc_connector = NotionSourceConnector(  # type: ignore
            connector_config=self.connector_config,
            read_config=self.read_config,
            processor_config=self.processor_config,
            retry_strategy_config=self.retry_strategy_config,
        )

        self.process_documents(source_doc_connector=source_doc_connector)
