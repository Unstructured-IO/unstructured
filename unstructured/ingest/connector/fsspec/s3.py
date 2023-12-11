import typing as t
from dataclasses import dataclass
from typing import Type

from unstructured.ingest.connector.fsspec.fsspec import (
    FsspecDestinationConnector,
    FsspecIngestDoc,
    FsspecSourceConnector,
    FsspecWriteConfig,
    SimpleFsspecConfig,
)
from unstructured.ingest.enhanced_dataclass import enhanced_field
from unstructured.ingest.interfaces import AccessConfig
from unstructured.utils import requires_dependencies


@dataclass
class S3AccessConfig(AccessConfig):
    anon: bool = enhanced_field(default=False, overload_name="anonymous")
    endpoint_url: t.Optional[str] = None
    key: t.Optional[str] = enhanced_field(default=None, sensitive=True)
    secret: t.Optional[str] = enhanced_field(default=None, sensitive=True)
    token: t.Optional[str] = enhanced_field(default=None, sensitive=True)


@dataclass
class S3WriteConfig(FsspecWriteConfig):
    pass


@dataclass
class SimpleS3Config(SimpleFsspecConfig):
    access_config: S3AccessConfig = enhanced_field(default=None)


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


@dataclass
class S3DestinationConnector(FsspecDestinationConnector):
    connector_config: SimpleS3Config
    write_config: S3WriteConfig

    @requires_dependencies(["s3fs", "fsspec"], extras="s3")
    def initialize(self):
        super().initialize()
