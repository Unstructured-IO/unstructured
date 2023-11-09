from unstructured.ingest.interfaces import BaseDestinationConnector
from unstructured.utils import requires_dependencies


@requires_dependencies(["chromadb"], extras="chroma")
def chroma_writer(
    # api_key: str,
    # index_name: str,
    # environment: str,
    db_path: str,
    collection_name: str,
    **kwargs,
) -> BaseDestinationConnector:
    from unstructured.ingest.connector.chroma import (
        ChromaDestinationConnector,
        ChromaWriteConfig,
        SimpleChromaConfig,
    )

    return ChromaDestinationConnector(
        connector_config=SimpleChromaConfig(
            # api_key=api_key,
            # index_name=index_name,
            # environment=environment,
            db_path=db_path,
            collection_name=collection_name,
        ),
        write_config=ChromaWriteConfig(
            # api_key=api_key,
            # index_name=index_name,
            # environment=environment,
            db_path=db_path,
            collection_name=collection_name,
        ),
    )