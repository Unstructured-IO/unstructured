import typing as t
from dataclasses import dataclass

from unstructured.ingest.enhanced_dataclass import EnhancedDataClassJsonMixin
from unstructured.ingest.interfaces import BaseDestinationConnector
from unstructured.ingest.runner.writers.base_writer import Writer

if t.TYPE_CHECKING:
    from unstructured.ingest.connector.elasticsearch import (
        ElasticsearchWriteConfig,
        SimpleElasticsearchConfig,
    )


@dataclass
class ElasticsearchWriter(Writer, EnhancedDataClassJsonMixin):
    connector_config: "SimpleElasticsearchConfig"
    write_config: "ElasticsearchWriteConfig"

    def get_connector(self, **kwargs) -> BaseDestinationConnector:
        from unstructured.ingest.connector.elasticsearch import (
            ElasticsearchDestinationConnector,
        )

        return ElasticsearchDestinationConnector(
            write_config=self.write_config,
            connector_config=self.connector_config,
        )
