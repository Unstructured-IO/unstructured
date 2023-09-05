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
class SimpleGcsConfig(SimpleFsspecConfig):
    pass


@dataclass
class GcsIngestDoc(FsspecIngestDoc):
    config: SimpleGcsConfig
    registry_name: str = "gcs"

    @SourceConnectionError.wrap
    @requires_dependencies(["gcsfs", "fsspec"], extras="gcs")
    def get_file(self):
        super().get_file()


class GcsSourceConnector(FsspecSourceConnector):
    ingest_doc_cls: Type[GcsIngestDoc] = GcsIngestDoc

    @requires_dependencies(["gcsfs", "fsspec"], extras="gcs")
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


class GcsDestinationConnector(FsspecDestinationConnector):
    @requires_dependencies(["gcsfs", "fsspec"], extras="gcs")
    def __init__(self, write_config: WriteConfig, connector_config: BaseConnectorConfig):
        super().__init__(write_config=write_config, connector_config=connector_config)
