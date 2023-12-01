import typing as t
from dataclasses import dataclass

from unstructured.ingest.interfaces import BaseDestinationConnector
from unstructured.ingest.runner.writers.base_writer import Writer

if t.TYPE_CHECKING:
    from unstructured.ingest.connector.azure_cognitive_search import (
        AzureCognitiveSearchWriteConfig,
        SimpleAzureCognitiveSearchStorageConfig,
    )


@dataclass
class AzureCognitiveSearchWriter(Writer):
    connector_config: t.Optional["SimpleAzureCognitiveSearchStorageConfig"] = None
    write_config: t.Optional["AzureCognitiveSearchWriteConfig"] = None

    def get_connector(self, overwrite: bool = False, **kwargs) -> BaseDestinationConnector:
        from unstructured.ingest.connector.azure_cognitive_search import (
            AzureCognitiveSearchDestinationConnector,
        )

        return AzureCognitiveSearchDestinationConnector(
            write_config=self.write_config,
            connector_config=self.connector_config,
        )
