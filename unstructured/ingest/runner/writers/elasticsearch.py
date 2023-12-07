from unstructured.ingest.interfaces import BaseDestinationConnector


def elasticsearch_writer(
    url: str,
    index_name: str,
    batch_size: int,
    num_processes: int,
    **kwargs,
) -> BaseDestinationConnector:
    from unstructured.ingest.connector.elasticsearch import (
        ElasticsearchDestinationConnector,
        ElasticsearchWriteConfig,
        SimpleElasticsearchConfig,
    )

    return ElasticsearchDestinationConnector(
        write_config=ElasticsearchWriteConfig(
            batch_size=batch_size,
            num_processes=num_processes,
        ),
        connector_config=SimpleElasticsearchConfig(
            url=url,
            index_name=index_name,
        ),
    )
