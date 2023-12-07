import typing as t
from dataclasses import dataclass

from unstructured.ingest.enhanced_dataclass import EnhancedDataClassJsonMixin
from unstructured.ingest.interfaces import BaseDestinationConnector
from unstructured.ingest.runner.writers.base_writer import Writer

if t.TYPE_CHECKING:
    from unstructured.ingest.connector.azure import (
        AzureWriteTextConfig,
        SimpleAzureBlobStorageConfig,
    )


@dataclass
class AzureWriter(Writer, EnhancedDataClassJsonMixin):
    connector_config: "SimpleAzureBlobStorageConfig"
    write_config: "AzureWriteTextConfig"

    def get_connector(self, overwrite: bool = False, **kwargs) -> BaseDestinationConnector:
        from unstructured.ingest.connector.azure import (
            AzureBlobStorageDestinationConnector,
            AzureWriteConfig,
        )

        return AzureBlobStorageDestinationConnector(
            write_config=AzureWriteConfig(write_text_config=self.write_config),
            connector_config=self.connector_config,
        )
