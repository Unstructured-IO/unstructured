import typing as t
from dataclasses import dataclass

from unstructured.ingest.enhanced_dataclass import EnhancedDataClassJsonMixin
from unstructured.ingest.interfaces import BaseDestinationConnector
from unstructured.ingest.runner.writers.base_writer import Writer

if t.TYPE_CHECKING:
    from unstructured.ingest.connector.mongodb import MongoDBWriteConfig, SimpleMongoDBStorageConfig


@dataclass
class MongodbWriter(Writer, EnhancedDataClassJsonMixin):
    write_config: "MongoDBWriteConfig"
    connector_config: "SimpleMongoDBStorageConfig"

    def get_connector(self, **kwargs) -> BaseDestinationConnector:
        from unstructured.ingest.connector.mongodb import (
            MongoDBDestinationConnector,
        )

        return MongoDBDestinationConnector(
            write_config=self.write_config,
            connector_config=self.connector_config,
        )
