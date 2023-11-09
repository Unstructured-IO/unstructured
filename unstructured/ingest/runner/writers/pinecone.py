from unstructured.ingest.interfaces import BaseDestinationConnector
from unstructured.utils import requires_dependencies


@requires_dependencies(["pinecone"], extras="pinecone")
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

    return PineconeDestinationConnector(
        connector_config=SimplePineconeConfig(
            api_key=api_key,
            index_name=index_name,
            environment=environment,
        ),
        write_config=PineconeWriteConfig(
            api_key=api_key,
            index_name=index_name,
            environment=environment,
            batch_size=batch_size,
            num_processes=num_processes,
        ),
    )
