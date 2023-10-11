import hashlib
import logging
import typing as t

from unstructured.ingest.logger import ingest_log_streaming_init, logger
from unstructured.ingest.runner.base_runner import Runner
from unstructured.ingest.runner.utils import update_download_dir_hash


class AirtableRunner(Runner):
    def run(
        self,
        personal_access_token: str,
        list_of_paths: t.Optional[str] = None,
        **kwargs,
    ):
        ingest_log_streaming_init(logging.DEBUG if self.processor_config.verbose else logging.INFO)

        hashed_dir_name = hashlib.sha256(
            personal_access_token.encode("utf-8"),
        )

        self.read_config.download_dir = update_download_dir_hash(
            connector_name="airtable",
            read_config=self.read_config,
            hashed_dir_name=hashed_dir_name,
            logger=logger,
        )

        from unstructured.ingest.connector.airtable import (
            AirtableSourceConnector,
            SimpleAirtableConfig,
        )

        source_doc_connector = AirtableSourceConnector(  # type: ignore
            processor_config=self.processor_config,
            connector_config=SimpleAirtableConfig(
                personal_access_token=personal_access_token,
                list_of_paths=list_of_paths,
            ),
            read_config=self.read_config,
        )

        self.process_documents(
            source_doc_connector=source_doc_connector,
        )
