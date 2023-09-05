from dataclasses import dataclass
from typing import Type

from unstructured.ingest.connector.fsspec import (
    FsspecDestinationConnector,
    FsspecIngestDoc,
    FsspecSourceConnector,
    SimpleFsspecConfig,
)
from unstructured.ingest.error import SourceConnectionError
from unstructured.ingest.interfaces2 import (
    BaseConnectorConfig,
    PartitionConfig,
    ReadConfig,
    WriteConfig,
)
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


class AzureBlobStorageSourceConnector(FsspecSourceConnector):
    ingest_doc_cls: Type[AzureBlobStorageIngestDoc] = AzureBlobStorageIngestDoc

    @requires_dependencies(["adlfs", "fsspec"], extras="azure")
    def __init__(
        self,
        read_config: ReadConfig,
        connector_config: BaseConnectorConfig,
        partition_config: PartitionConfig,
    ):
        super().__init__(
            read_config=read_config,
            connector_config=connector_config,
            partition_config=partition_config,
        )


class AzureBlobStorageDestinationConnector(FsspecDestinationConnector):
    @requires_dependencies(["adlfs", "fsspec"], extras="azure")
    def __init__(self, write_config: WriteConfig, connector_config: BaseConnectorConfig):
        super().__init__(write_config=write_config, connector_config=connector_config)
