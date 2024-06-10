from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from time import time
from typing import Any, Generator, Optional

from unstructured.documents.elements import DataSourceMetadata
from unstructured.ingest.enhanced_dataclass import enhanced_field
from unstructured.ingest.v2.interfaces import DownloadResponse, FileData, UploadContent
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
from unstructured.utils import requires_dependencies

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
    access_config: S3AccessConfig = enhanced_field(
        sensitive=True, default_factory=lambda: S3AccessConfig()
    )
    endpoint_url: Optional[str] = None
    anonymous: bool = False
    connector_type: str = CONNECTOR_TYPE

    def get_access_config(self) -> dict[str, Any]:
        access_configs: dict[str, Any] = {"anon": self.anonymous}
        if self.endpoint_url:
            access_configs["endpoint_url"] = self.endpoint_url

        # Avoid injecting None by filtering out k,v pairs where the value is None
        access_configs.update({k: v for k, v in self.access_config.to_dict().items() if v})
        return access_configs


@dataclass
class S3Indexer(FsspecIndexer):
    connection_config: S3ConnectionConfig
    index_config: S3IndexerConfig
    connector_type: str = CONNECTOR_TYPE

    @requires_dependencies(["s3fs", "fsspec"], extras="s3")
    def __post_init__(self):
        super().__post_init__()

    def get_metadata(self, path: str) -> DataSourceMetadata:
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

    @requires_dependencies(["s3fs", "fsspec"], extras="s3")
    def run(self, **kwargs: Any) -> Generator[FileData, None, None]:
        return super().run(**kwargs)


@dataclass
class S3DownloaderConfig(FsspecDownloaderConfig):
    pass


@dataclass
class S3Downloader(FsspecDownloader):
    protocol: str = "s3"
    connection_config: S3ConnectionConfig
    connector_type: str = CONNECTOR_TYPE
    download_config: Optional[S3DownloaderConfig] = field(default_factory=S3DownloaderConfig)

    @requires_dependencies(["s3fs", "fsspec"], extras="s3")
    def __post_init__(self):
        super().__post_init__()

    @requires_dependencies(["s3fs", "fsspec"], extras="s3")
    def run(self, file_data: FileData, **kwargs: Any) -> DownloadResponse:
        return super().run(file_data=file_data, **kwargs)

    @requires_dependencies(["s3fs", "fsspec"], extras="s3")
    async def run_async(self, file_data: FileData, **kwargs: Any) -> DownloadResponse:
        return await super().run_async(file_data=file_data, **kwargs)


@dataclass
class S3UploaderConfig(FsspecUploaderConfig):
    pass


@dataclass
class S3Upload(FsspecUploader):
    connection_config: S3ConnectionConfig
    upload_config: S3UploaderConfig = field(default=None)

    @requires_dependencies(["s3fs", "fsspec"], extras="s3")
    def __post_init__(self):
        super().__post_init__()

    @requires_dependencies(["s3fs", "fsspec"], extras="s3")
    def run(self, contents: list[UploadContent], **kwargs: Any) -> None:
        return super().run(contents=contents, **kwargs)

    @requires_dependencies(["s3fs", "fsspec"], extras="s3")
    async def run_async(self, path: Path, file_data: FileData, **kwargs: Any) -> None:
        return await super().run_async(path=path, file_data=file_data, **kwargs)


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
    entry=DestinationRegistryEntry(
        uploader=S3Upload,
        uploader_config=S3UploaderConfig,
        connection_config=S3ConnectionConfig,
    ),
)
