import hashlib
import typing as t
from dataclasses import dataclass

from unstructured.ingest.interfaces import BaseSourceConnector
from unstructured.ingest.logger import logger
from unstructured.ingest.runner.base_runner import Runner
from unstructured.ingest.runner.utils import update_download_dir_hash

if t.TYPE_CHECKING:
    from unstructured.ingest.connector.biomed import SimpleBiomedConfig


@dataclass
class BiomedRunner(Runner):
    connector_config: "SimpleBiomedConfig"

    def update_read_config(self):
        base_path = (
            self.connector_config.path
            if self.connector_config.path
            else "{}-{}-{}".format(
                self.connector_config.api_id if self.connector_config.api_id else "",
                self.connector_config.api_from if self.connector_config.api_from else "",
                self.connector_config.api_until if self.connector_config.api_until else "",
            )
        )

        hashed_dir_name = hashlib.sha256(
            base_path.encode("utf-8"),
        )

        self.read_config.download_dir = update_download_dir_hash(
            connector_name="biomed",
            read_config=self.read_config,
            hashed_dir_name=hashed_dir_name,
            logger=logger,
        )

    def get_source_connector_cls(self) -> t.Type[BaseSourceConnector]:
        from unstructured.ingest.connector.biomed import (
            BiomedSourceConnector,
        )

        return BiomedSourceConnector
