import hashlib
import typing as t
from dataclasses import dataclass

from unstructured.ingest.interfaces import BaseSourceConnector
from unstructured.ingest.logger import logger
from unstructured.ingest.runner.base_runner import Runner
from unstructured.ingest.runner.utils import update_download_dir_hash

if t.TYPE_CHECKING:
    from unstructured.ingest.connector.google_drive import SimpleGoogleDriveConfig


@dataclass
class GoogleDriveRunner(Runner):
    connector_config: "SimpleGoogleDriveConfig"

    def update_read_config(self):
        hashed_dir_name = hashlib.sha256(
            self.connector_config.drive_id.encode("utf-8"),
        )

        self.read_config.download_dir = update_download_dir_hash(
            connector_name="google_drive",
            read_config=self.read_config,
            hashed_dir_name=hashed_dir_name,
            logger=logger,
        )

    def get_source_connector_cls(self) -> t.Type[BaseSourceConnector]:
        from unstructured.ingest.connector.google_drive import (
            GoogleDriveSourceConnector,
        )

        return GoogleDriveSourceConnector
