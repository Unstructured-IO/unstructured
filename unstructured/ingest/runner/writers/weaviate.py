import typing as t

from unstructured.utils import requires_dependencies


@requires_dependencies(["weaviate"], extras="weaviate")
def weaviate_writer(
    host_url: str,
    class_name: str,
    auth_keys: t.Optional[t.List[str]] = None,
    additional_headers: t.Optional[t.List[str]] = None,
    **kwargs,
):
    from unstructured.ingest.connector.weaviate import (
        SimpleWeaviateConfig,
        WeaviateDestinationConnector,
        WeaviateWriteConfig,
    )

    return WeaviateDestinationConnector(
        write_config=WeaviateWriteConfig(class_name=class_name),
        connector_config=SimpleWeaviateConfig(
            host_url=host_url,
            auth_keys=auth_keys,
            additional_headers=additional_headers,
        ),
    )
