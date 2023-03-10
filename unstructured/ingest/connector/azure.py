from dataclasses import dataclass
from typing import Type

from unstructured.ingest.connector.fsspec import (
    FsspecConnector,
    FsspecIngestDoc,
    SimpleFsspecConfig,
)
from unstructured.utils import requires_dependencies


@dataclass
class SimpleAzureBlobStorageConfig(SimpleFsspecConfig):
    pass


class AzureBlobStorageIngestDoc(FsspecIngestDoc):
    @requires_dependencies(["adlfs", "fsspec"], extras="azure")
    def get_file(self):
        super().get_file()


@requires_dependencies(["adlfs", "fsspec"], extras="azure")
class AzureBlobStorageConnector(FsspecConnector):
    ingest_doc_cls: Type[AzureBlobStorageIngestDoc] = AzureBlobStorageIngestDoc

    def __init__(
        self,
        config: SimpleAzureBlobStorageConfig,
    ) -> None:
        super().__init__(config=config)
