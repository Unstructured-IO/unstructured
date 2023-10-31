import hashlib
import logging
import typing as t

from unstructured.ingest.logger import ingest_log_streaming_init, logger
from unstructured.ingest.runner.base_runner import Runner
from unstructured.ingest.runner.utils import update_download_dir_hash


class GoogleDriveRunner(Runner):
    def run(
        self,
        service_account_key: t.Union[str, dict],
        drive_id: str,
        recursive: bool = False,
        extension: t.Optional[str] = None,
        **kwargs,
    ):
        ingest_log_streaming_init(logging.DEBUG if self.processor_config.verbose else logging.INFO)

        hashed_dir_name = hashlib.sha256(
            drive_id.encode("utf-8"),
        )

        self.read_config.download_dir = update_download_dir_hash(
            connector_name="google_drive",
            read_config=self.read_config,
            hashed_dir_name=hashed_dir_name,
            logger=logger,
        )

        from unstructured.ingest.connector.google_drive import (
            GoogleDriveSourceConnector,
            SimpleGoogleDriveConfig,
        )

        source_doc_connector = GoogleDriveSourceConnector(  # type: ignore
            connector_config=SimpleGoogleDriveConfig(
                drive_id=drive_id,
                service_account_key=service_account_key,
                recursive=recursive,
                extension=extension,
            ),
            read_config=self.read_config,
            processor_config=self.processor_config,
        )

        self.process_documents(source_doc_connector=source_doc_connector)
