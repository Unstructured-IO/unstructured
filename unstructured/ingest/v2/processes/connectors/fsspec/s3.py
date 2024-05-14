from contextlib import suppress
from dataclasses import dataclass, field
from time import time
from typing import Any, Optional

from unstructured.documents.elements import DataSourceMetadata
from unstructured.ingest.enhanced_dataclass import enhanced_field
from unstructured.ingest.v2.processes.connectors.fsspec.fsspec import (
    FsspecAccessConfig,
    FsspecConnectionConfig,
    FsspecDestination,
    FsspecDownloader,
    FsspecDownloaderConfig,
    FsspecIndexer,
    FsspecIndexerConfig,
    FsspecSource,
    FsspecUploader,
    FsspecUploaderConfig,
)

CONNECTOR_TYPE = "s3"


@dataclass
class S3IndexerConfig(FsspecIndexerConfig):
    pass


@dataclass
class S3AccessConfig(FsspecAccessConfig):
    key: Optional[str] = None
    secret: Optional[str] = None
    token: Optional[str] = None


@dataclass
class S3ConnectionConfig(FsspecConnectionConfig):
    supported_protocols: list[str] = field(default_factory=lambda: ["s3", "s3a"])
    access_config: S3AccessConfig = enhanced_field(sensitive=True, default_factory=S3AccessConfig)
    endpoint_url: Optional[str] = None
    anonymous: bool = False
    connector_type: str = CONNECTOR_TYPE

    def get_access_config(self) -> dict[str, Any]:
        access_configs = {"anon": self.anonymous}
        if self.endpoint_url:
            access_configs["endpoint"] = self.endpoint_url

        access_configs.update(self.access_config.to_dict())
        return access_configs


@dataclass
class S3Indexer(FsspecIndexer):
    connection_config: S3ConnectionConfig
    index_config: S3IndexerConfig = field(default_factory=S3IndexerConfig)
    connector_type: str = CONNECTOR_TYPE

    def get_metadata(self, path) -> DataSourceMetadata:
        date_created = None
        date_modified = None
        with suppress(NotImplementedError):
            date_created = self.fs.modified(path).timestamp()
            date_modified = self.fs.modified(path).timestamp()

        etag = self.fs.info(path).get("ETag", None)
        etag = etag.rstrip('"').lstrip('"')
        return DataSourceMetadata(
            date_created=date_created,
            date_modified=date_modified,
            date_processed=str(time()),
            version=etag,
            url=f"{self.index_config.protocol}://{path}",
        )


@dataclass
class S3DownloaderConfig(FsspecDownloaderConfig):
    pass


@dataclass
class S3Downloader(FsspecDownloader):
    protocol: str = "s3"
    connection_config: S3ConnectionConfig
    connector_type: str = CONNECTOR_TYPE
    download_config: Optional[S3DownloaderConfig] = field(default_factory=S3DownloaderConfig)


@dataclass(kw_only=True)
class S3Source(FsspecSource):
    indexer: S3Indexer
    downloader: S3Downloader
    connector_type: str = CONNECTOR_TYPE


@dataclass
class S3UploaderConfig(FsspecUploaderConfig):
    pass


@dataclass
class S3Upload(FsspecUploader):
    connection_config: S3ConnectionConfig
    upload_config: S3UploaderConfig = field(default_factory=S3UploaderConfig)


@dataclass(kw_only=True)
class S3Destination(FsspecDestination):
    uploader: S3Upload
    connector_type: str = CONNECTOR_TYPE
