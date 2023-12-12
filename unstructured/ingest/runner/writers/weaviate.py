import typing as t
from dataclasses import dataclass

from unstructured.ingest.interfaces import BaseDestinationConnector
from unstructured.ingest.runner.writers.base_writer import Writer

if t.TYPE_CHECKING:
    from unstructured.ingest.connector.weaviate import SimpleWeaviateConfig, WeaviateWriteConfig


@dataclass
class WeaviateWriter(Writer):
    write_config: "WeaviateWriteConfig"
    connector_config: "SimpleWeaviateConfig"

    def get_connector_cls(self) -> t.Type[BaseDestinationConnector]:
        from unstructured.ingest.connector.weaviate import (
            WeaviateDestinationConnector,
        )

        return WeaviateDestinationConnector
