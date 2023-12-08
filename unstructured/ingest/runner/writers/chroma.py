from unstructured.ingest.interfaces import BaseDestinationConnector
from unstructured.utils import requires_dependencies


import typing as t
from dataclasses import dataclass

from unstructured.ingest.enhanced_dataclass import EnhancedDataClassJsonMixin
from unstructured.ingest.interfaces import BaseDestinationConnector
from unstructured.ingest.runner.writers.base_writer import Writer

if t.TYPE_CHECKING:
    from unstructured.ingest.connector.pinecone import PineconeWriteConfig, SimplePineconeConfig


@dataclass
class ChromaWriter(Writer, EnhancedDataClassJsonMixin):
    write_config: "ChromaWriteConfig"
    connector_config: "SimpleChromaConfig"

    def get_connector(self, **kwargs) -> BaseDestinationConnector:
        from unstructured.ingest.connector.chroma import (
            ChromaDestinationConnector,
        )

        return ChromaDestinationConnector(
            connector_config=self.connector_config,
            write_config=self.write_config,
        )

def chroma_writer(
    # api_key: str,
    # index_name: str,
    # environment: str,
    db_path: str,
    collection_name: str,
    batch_size: int,
    # num_processes: int, # maybe
    **kwargs,
) -> BaseDestinationConnector:
    from unstructured.ingest.connector.chroma import (
        ChromaDestinationConnector,
        ChromaWriteConfig,
        SimpleChromaConfig,
    )

    connector_config = SimpleChromaConfig(
        # api_key=api_key,
        # index_name=index_name,
        # environment=environment,
        db_path=db_path,
        collection_name=collection_name,
    )

    return ChromaDestinationConnector(
        connector_config=connector_config,
        write_config=ChromaWriteConfig(
            # api_key=api_key,
            # index_name=index_name,
            # environment=environment,
            db_path=db_path,
            collection_name=collection_name,
            batch_size=batch_size,
            # num_processes=num_processes, # maybe
        ),
    )