import typing as t
from dataclasses import dataclass

from unstructured.ingest.enhanced_dataclass import EnhancedDataClassJsonMixin
from unstructured.ingest.interfaces import BaseDestinationConnector
from unstructured.ingest.runner.writers.base_writer import Writer

if t.TYPE_CHECKING:
    from unstructured.ingest.connector.pinecone import PineconeWriteConfig, SimplePineconeConfig


@dataclass
class PineconeWriter(Writer, EnhancedDataClassJsonMixin):
    write_config: "PineconeWriteConfig"
    connector_config: "SimplePineconeConfig"

    def get_connector(self, **kwargs) -> BaseDestinationConnector:
        from unstructured.ingest.connector.pinecone import (
            PineconeDestinationConnector,
        )

        return PineconeDestinationConnector(
            connector_config=self.connector_config,
            write_config=self.write_config,
        )


def pinecone_writer(
    api_key: str,
    index_name: str,
    environment: str,
    batch_size: int,
    num_processes: int,
    **kwargs,
) -> BaseDestinationConnector:
    from unstructured.ingest.connector.pinecone import (
        PineconeDestinationConnector,
        PineconeWriteConfig,
        SimplePineconeConfig,
    )

    connector_config = SimplePineconeConfig(
        api_key=api_key,
        index_name=index_name,
        environment=environment,
    )

    return PineconeDestinationConnector(
        connector_config=connector_config,
        write_config=PineconeWriteConfig(
            connector_config=connector_config,
            batch_size=batch_size,
            num_processes=num_processes,
        ),
    )
