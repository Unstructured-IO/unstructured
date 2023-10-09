import typing as t
from dataclasses import dataclass

from unstructured.ingest.connector.fsspec import (
    FsspecDestinationConnector,
    FsspecIngestDoc,
    FsspecSourceConnector,
    SimpleFsspecConfig,
)
from unstructured.ingest.error import SourceConnectionError
from unstructured.utils import requires_dependencies


@dataclass
class SimpleAzureBlobStorageConfig(SimpleFsspecConfig):
    pass


@dataclass
class AzureBlobStorageIngestDoc(FsspecIngestDoc):
    connector_config: SimpleAzureBlobStorageConfig
    registry_name: str = "azure"

    @SourceConnectionError.wrap
    @requires_dependencies(["adlfs", "fsspec"], extras="azure")
    def get_file(self):
        super().get_file()


@dataclass
class AzureBlobStorageSourceConnector(FsspecSourceConnector):
    connector_config: SimpleAzureBlobStorageConfig

    def __post_init__(self):
        self.ingest_doc_cls: t.Type[AzureBlobStorageIngestDoc] = AzureBlobStorageIngestDoc


@dataclass
class AzureBlobStorageDestinationConnector(FsspecDestinationConnector):
    connector_config: SimpleAzureBlobStorageConfig
