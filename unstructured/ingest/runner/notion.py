import hashlib
import typing as t
from dataclasses import dataclass

from unstructured.ingest.interfaces import BaseSourceConnector
from unstructured.ingest.logger import logger
from unstructured.ingest.runner.base_runner import Runner
from unstructured.ingest.runner.utils import update_download_dir_hash

if t.TYPE_CHECKING:
    from unstructured.ingest.connector.notion.connector import SimpleNotionConfig


@dataclass
class NotionRunner(Runner):
    connector_config: "SimpleNotionConfig"

    def update_read_config(self):
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

    def get_source_connector_cls(self) -> t.Type[BaseSourceConnector]:
        from unstructured.ingest.connector.notion.connector import (
            NotionSourceConnector,
        )

        return NotionSourceConnector

    def get_source_connector(self) -> BaseSourceConnector:
        source_connector_cls = self.get_source_connector_cls()
        return source_connector_cls(
            processor_config=self.processor_config,
            connector_config=self.connector_config,
            read_config=self.read_config,
            retry_strategy_config=self.retry_strategy_config,
        )
