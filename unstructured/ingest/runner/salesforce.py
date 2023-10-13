import hashlib
import logging
import typing as t

from unstructured.ingest.logger import ingest_log_streaming_init, logger
from unstructured.ingest.runner.base_runner import Runner
from unstructured.ingest.runner.utils import update_download_dir_hash


class SalesforceRunner(Runner):
    def run(
        self,
        username: str,
        consumer_key: str,
        private_key_path: str,
        categories: t.List[str],
        recursive: bool = False,
        **kwargs,
    ):
        ingest_log_streaming_init(logging.DEBUG if self.processor_config.verbose else logging.INFO)

        hashed_dir_name = hashlib.sha256(username.encode("utf-8"))

        self.read_config.download_dir = update_download_dir_hash(
            connector_name="salesforce",
            read_config=self.read_config,
            hashed_dir_name=hashed_dir_name,
            logger=logger,
        )

        from unstructured.ingest.connector.salesforce import (
            SalesforceSourceConnector,
            SimpleSalesforceConfig,
        )

        source_doc_connector = SalesforceSourceConnector(  # type: ignore
            connector_config=SimpleSalesforceConfig(
                categories=categories,
                username=username,
                consumer_key=consumer_key,
                private_key_path=private_key_path,
                recursive=recursive,
            ),
            read_config=self.read_config,
            processor_config=self.processor_config,
        )

        self.process_documents(source_doc_connector=source_doc_connector)
