import typing as t
from dataclasses import dataclass

from unstructured.ingest.enhanced_dataclass import EnhancedDataClassJsonMixin
from unstructured.ingest.interfaces import BaseDestinationConnector
from unstructured.ingest.runner.writers.base_writer import Writer

if t.TYPE_CHECKING:
    from unstructured.ingest.connector.weaviate import SimpleWeaviateConfig, WeaviateWriteConfig


@dataclass
class WeaviateWriter(Writer, EnhancedDataClassJsonMixin):
    write_config: "WeaviateWriteConfig"
    connector_config: "SimpleWeaviateConfig"

    def get_connector(self, **kwargs) -> BaseDestinationConnector:
        from unstructured.ingest.connector.weaviate import (
            WeaviateDestinationConnector,
        )

        return WeaviateDestinationConnector(
            write_config=self.write_config,
            connector_config=self.connector_config,
        )
