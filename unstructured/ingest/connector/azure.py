from dataclasses import dataclass
from typing import Type

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
    registry_name: str = "azure"

    @SourceConnectionError.wrap
    @requires_dependencies(["adlfs", "fsspec"], extras="azure")
    def get_file(self):
        super().get_file()


@dataclass
class AzureBlobStorageSourceConnector(FsspecSourceConnector):
    ingest_doc_cls: Type[AzureBlobStorageIngestDoc] = AzureBlobStorageIngestDoc


@dataclass
class AzureBlobStorageDestinationConnector(FsspecDestinationConnector):
    pass
