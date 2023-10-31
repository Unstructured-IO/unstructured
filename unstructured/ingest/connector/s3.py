from dataclasses import dataclass
from typing import Type

from unstructured.ingest.connector.fsspec import (
    FsspecDestinationConnector,
    FsspecIngestDoc,
    FsspecSourceConnector,
    SimpleFsspecConfig,
)
from unstructured.utils import requires_dependencies


@dataclass
class SimpleS3Config(SimpleFsspecConfig):
    pass


@dataclass
class S3IngestDoc(FsspecIngestDoc):
    connector_config: SimpleS3Config
    remote_file_path: str
    registry_name: str = "s3"

    @requires_dependencies(["s3fs", "fsspec"], extras="s3")
    def get_file(self):
        super().get_file()


@dataclass
class S3SourceConnector(FsspecSourceConnector):
    connector_config: SimpleS3Config

    def __post_init__(self):
        self.ingest_doc_cls: Type[S3IngestDoc] = S3IngestDoc


@requires_dependencies(["s3fs", "fsspec"], extras="s3")
@dataclass
class S3DestinationConnector(FsspecDestinationConnector):
    connector_config: SimpleS3Config
