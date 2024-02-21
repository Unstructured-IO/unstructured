import typing as t
from dataclasses import dataclass

from unstructured.ingest.interfaces import BaseDestinationConnector
from unstructured.ingest.runner.writers.base_writer import Writer

if t.TYPE_CHECKING:
    from unstructured.ingest.connector.fsspec.azure import (
        AzureWriteConfig,
        SimpleAzureBlobStorageConfig,
    )


@dataclass
class AzureWriter(Writer):
    connector_config: "SimpleAzureBlobStorageConfig"
    write_config: "AzureWriteConfig"

    def get_connector_cls(self) -> t.Type[BaseDestinationConnector]:
        from unstructured.ingest.connector.fsspec.azure import (
            AzureBlobStorageDestinationConnector,
        )

        return AzureBlobStorageDestinationConnector
