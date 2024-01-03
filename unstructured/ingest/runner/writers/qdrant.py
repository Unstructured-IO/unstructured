import typing as t
from dataclasses import dataclass

from unstructured.ingest.interfaces import BaseDestinationConnector
from unstructured.ingest.runner.writers.base_writer import Writer

if t.TYPE_CHECKING:
    from unstructured.ingest.connector.qdrant import QdrantWriteConfig, SimpleQdrantConfig


@dataclass
class QdrantWriter(Writer):
    write_config: "QdrantWriteConfig"
    connector_config: "SimpleQdrantConfig"

    def get_connector_cls(self) -> t.Type[BaseDestinationConnector]:
        from unstructured.ingest.connector.qdrant import QdrantDestinationConnector

        return QdrantDestinationConnector
