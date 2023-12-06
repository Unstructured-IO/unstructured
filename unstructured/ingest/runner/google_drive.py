import hashlib
import logging
import typing as t

from unstructured.ingest.logger import ingest_log_streaming_init, logger
from unstructured.ingest.runner.base_runner import Runner
from unstructured.ingest.runner.utils import update_download_dir_hash

if t.TYPE_CHECKING:
    from unstructured.ingest.connector.google_drive import SimpleGoogleDriveConfig


class GoogleDriveRunner(Runner):
    connector_config: "SimpleGoogleDriveConfig"

    def run(
        self,
        **kwargs,
    ):
        ingest_log_streaming_init(logging.DEBUG if self.processor_config.verbose else logging.INFO)

        hashed_dir_name = hashlib.sha256(
            self.connector_config.drive_id.encode("utf-8"),
        )

        self.read_config.download_dir = update_download_dir_hash(
            connector_name="google_drive",
            read_config=self.read_config,
            hashed_dir_name=hashed_dir_name,
            logger=logger,
        )

        from unstructured.ingest.connector.google_drive import (
            GoogleDriveSourceConnector,
        )

        source_doc_connector = GoogleDriveSourceConnector(  # type: ignore
            connector_config=self.connector_config,
            read_config=self.read_config,
            processor_config=self.processor_config,
        )

        self.process_documents(source_doc_connector=source_doc_connector)
