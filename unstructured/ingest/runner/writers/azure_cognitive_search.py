def azure_cognitive_search_writer(
    endpoint: str,
    key: str,
    index: str,
    **kwargs,
):
    from unstructured.ingest.connector.azure_cognitive_search import (
        AzureCognitiveSearchDestinationConnector,
        AzureCognitiveSearchWriteConfig,
        SimpleAzureCognitiveSearchStorageConfig,
    )

    return AzureCognitiveSearchDestinationConnector(
        write_config=AzureCognitiveSearchWriteConfig(
            index=index,
        ),
        connector_config=SimpleAzureCognitiveSearchStorageConfig(
            endpoint=endpoint,
            key=key,
        ),
    )
