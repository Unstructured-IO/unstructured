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
class SimpleGcsConfig(SimpleFsspecConfig):
    pass


@dataclass
class GcsIngestDoc(FsspecIngestDoc):
    connector_config: SimpleGcsConfig
    registry_name: str = "gcs"

    @SourceConnectionError.wrap
    @requires_dependencies(["gcsfs", "fsspec"], extras="gcs")
    def get_file(self):
        super().get_file()


@dataclass
class GcsSourceConnector(FsspecSourceConnector):
    connector_config: SimpleGcsConfig

    def __post_init__(self):
        self.ingest_doc_cls: Type[GcsIngestDoc] = GcsIngestDoc


@dataclass
class GcsDestinationConnector(FsspecDestinationConnector):
    connector_config: SimpleGcsConfig
