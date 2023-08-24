from dataclasses import dataclass
from typing import Type

from unstructured.ingest.connector.fsspec import (
    FsspecConnector,
    FsspecIngestDoc,
    SimpleFsspecConfig,
)
from unstructured.ingest.interfaces import StandardConnectorConfig


@dataclass
class SimpleAzureBlobStorageConfig(SimpleFsspecConfig):
    pass


class AzureBlobStorageIngestDoc(FsspecIngestDoc):
    def get_file(self):
        super().get_file()


class AzureBlobStorageConnector(FsspecConnector):
    ingest_doc_cls: Type[AzureBlobStorageIngestDoc] = AzureBlobStorageIngestDoc

    def __init__(
        self,
        standard_config: StandardConnectorConfig,
        config: SimpleAzureBlobStorageConfig,
    ) -> None:
        super().__init__(standard_config=standard_config, config=config)
