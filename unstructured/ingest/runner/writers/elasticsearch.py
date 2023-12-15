import typing as t
from dataclasses import dataclass

from unstructured.ingest.interfaces import BaseDestinationConnector
from unstructured.ingest.runner.writers.base_writer import Writer

if t.TYPE_CHECKING:
    from unstructured.ingest.connector.elasticsearch import (
        ElasticsearchWriteConfig,
        SimpleElasticsearchConfig,
    )


@dataclass
class ElasticsearchWriter(Writer):
    connector_config: "SimpleElasticsearchConfig"
    write_config: "ElasticsearchWriteConfig"

    def get_connector_cls(self) -> BaseDestinationConnector:
        from unstructured.ingest.connector.elasticsearch import (
            ElasticsearchDestinationConnector,
        )

        return ElasticsearchDestinationConnector
