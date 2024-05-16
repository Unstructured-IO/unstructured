from dataclasses import dataclass, field
from datetime import datetime
from time import time
from typing import Any, Optional

from unstructured.documents.elements import DataSourceMetadata
from unstructured.ingest.enhanced_dataclass import enhanced_field
from unstructured.ingest.v2.processes.connector_registry import (
    DestinationRegistryEntry,
    SourceRegistryEntry,
    add_destination_entry,
    add_source_entry,
)
from unstructured.ingest.v2.processes.connectors.fsspec.fsspec import (
    FsspecAccessConfig,
    FsspecConnectionConfig,
    FsspecDownloader,
    FsspecDownloaderConfig,
    FsspecIndexer,
    FsspecIndexerConfig,
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
        access_configs: dict[str, Any] = {"anon": self.anonymous}
        if self.endpoint_url:
            access_configs["endpoint_url"] = self.endpoint_url

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
        try:
            modified: Optional[datetime] = self.fs.modified(path)
            if modified:
                date_created = str(modified.timestamp())
                date_modified = str(modified.timestamp())
        except NotImplementedError:
            pass

        version = None
        info: dict[str, Any] = self.fs.info(path)
        if etag := info.get("ETag"):
            version = str(etag).rstrip('"').lstrip('"')
        return DataSourceMetadata(
            date_created=date_created,
            date_modified=date_modified,
            date_processed=str(time()),
            version=version,
            url=f"{self.index_config.protocol}://{path}",
            record_locator={
                "protocol": self.index_config.protocol,
                "remote_file_path": self.index_config.remote_url,
            },
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


@dataclass
class S3UploaderConfig(FsspecUploaderConfig):
    pass


@dataclass
class S3Upload(FsspecUploader):
    connection_config: S3ConnectionConfig
    upload_config: S3UploaderConfig = field(default_factory=S3UploaderConfig)


add_source_entry(
    source_type=CONNECTOR_TYPE,
    entry=SourceRegistryEntry(
        indexer=S3Indexer,
        indexer_config=S3IndexerConfig,
        downloader=S3Downloader,
        downloader_config=S3DownloaderConfig,
        connection_config=S3ConnectionConfig,
    ),
)

add_destination_entry(
    destination_type=CONNECTOR_TYPE,
    entry=DestinationRegistryEntry(uploader=S3Upload, uploader_config=S3UploaderConfig),
)
