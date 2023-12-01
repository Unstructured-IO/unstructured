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
    fsspec_config: t.Optional["SimpleAzureBlobStorageConfig"] = None
    write_config: t.Optional["AzureWriteTextConfig"] = None

    def get_connector(self, overwrite: bool = False, **kwargs) -> BaseDestinationConnector:
        from unstructured.ingest.connector.azure import (
            AzureBlobStorageDestinationConnector,
        )
        from unstructured.ingest.connector.fsspec import FsspecWriteConfig

        return AzureBlobStorageDestinationConnector(
            write_config=FsspecWriteConfig(write_text_config=self.write_config),
            connector_config=self.fsspec_config,
        )
