import typing as t

from unstructured.utils import requires_dependencies


@requires_dependencies(["weaviate"], extras="weaviate")
def weaviate_writer(
    host_url: str,
    class_name: str,
    batch_size: int = 100,
    auth_keys: t.Optional[t.List[str]] = None,
    **kwargs,
):
    from unstructured.ingest.connector.weaviate import (
        SimpleWeaviateConfig,
        WeaviateDestinationConnector,
        WeaviateWriteConfig,
    )

    return WeaviateDestinationConnector(
        write_config=WeaviateWriteConfig(batch_size=batch_size),
        connector_config=SimpleWeaviateConfig(
            host_url=host_url,
            class_name=class_name,
            auth_keys=auth_keys,
        ),
    )
