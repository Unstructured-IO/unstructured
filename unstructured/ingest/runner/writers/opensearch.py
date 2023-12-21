import typing as t
from dataclasses import dataclass

from unstructured.ingest.interfaces import BaseDestinationConnector
from unstructured.ingest.runner.writers.base_writer import Writer

if t.TYPE_CHECKING:
    from unstructured.ingest.connector.opensearch import (
        OpenSearchWriteConfig,
        SimpleOpenSearchConfig,
    )


@dataclass
class OpenSearchWriter(Writer):
    connector_config: "SimpleOpenSearchConfig"
    write_config: "OpenSearchWriteConfig"

    def get_connector_cls(self) -> BaseDestinationConnector:
        from unstructured.ingest.connector.opensearch import (
            OpenSearchDestinationConnector,
        )

        return OpenSearchDestinationConnector
