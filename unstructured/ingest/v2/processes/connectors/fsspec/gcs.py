from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Generator, Optional, Union

from unstructured.ingest.enhanced_dataclass import enhanced_field
from unstructured.ingest.utils.string_and_date_utils import json_to_dict
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

CONNECTOR_TYPE = "gcs"


@dataclass
class GcsIndexerConfig(FsspecIndexerConfig):
    pass


@dataclass
class GcsAccessConfig(FsspecAccessConfig):
    service_account_key: Optional[str] = None
    token: Union[str, dict, None] = field(init=False, default=None)

    def __post_init__(self):
        ALLOWED_AUTH_VALUES = "google_default", "cache", "anon", "browser", "cloud"

        # Case: null value
        if not self.service_account_key:
            return

        # Case: one of auth constants
        if self.service_account_key in ALLOWED_AUTH_VALUES:
            self.token = self.service_account_key
            return

        # Case: token as json
        if isinstance(json_to_dict(self.service_account_key), dict):
            self.token = json_to_dict(self.service_account_key)
            return

        # Case: path to token
        if Path(self.service_account_key).is_file():
            self.token = self.service_account_key
            return

        raise ValueError("Invalid auth token value")


@dataclass
class GcsConnectionConfig(FsspecConnectionConfig):
    supported_protocols: list[str] = field(default_factory=lambda: ["gs", "gcs"])
    access_config: GcsAccessConfig = enhanced_field(
        sensitive=True, default_factory=lambda: GcsAccessConfig()
    )
    connector_type: str = CONNECTOR_TYPE


@dataclass
class GcsIndexer(FsspecIndexer):
    connection_config: GcsConnectionConfig
    index_config: GcsIndexerConfig
    connector_type: str = CONNECTOR_TYPE

    @requires_dependencies(["gcsfs", "fsspec"], extras="gcs")
    def run(self, **kwargs: Any) -> Generator[FileData, None, None]:
        return super().run(**kwargs)


@dataclass
class GcsDownloaderConfig(FsspecDownloaderConfig):
    pass


@dataclass
class GcsDownloader(FsspecDownloader):
    protocol: str = "gcs"
    connection_config: GcsConnectionConfig
    connector_type: str = CONNECTOR_TYPE
    download_config: Optional[GcsDownloaderConfig] = field(default_factory=GcsDownloaderConfig)

    @requires_dependencies(["gcsfs", "fsspec"], extras="gcs")
    def run(self, file_data: FileData, **kwargs: Any) -> DownloadResponse:
        return super().run(file_data=file_data, **kwargs)

    @requires_dependencies(["gcsfs", "fsspec"], extras="gcs")
    async def run_async(self, file_data: FileData, **kwargs: Any) -> DownloadResponse:
        return await super().run_async(file_data=file_data, **kwargs)


@dataclass
class GcsUploaderConfig(FsspecUploaderConfig):
    pass


@dataclass
class GcsUploader(FsspecUploader):
    connector_type: str = CONNECTOR_TYPE
    connection_config: GcsConnectionConfig
    upload_config: GcsUploaderConfig = field(default=None)

    @requires_dependencies(["gcsfs", "fsspec"], extras="gcs")
    def __post_init__(self):
        super().__post_init__()

    @requires_dependencies(["gcsfs", "fsspec"], extras="gcs")
    def run(self, contents: list[UploadContent], **kwargs: Any) -> None:
        return super().run(contents=contents, **kwargs)

    @requires_dependencies(["gcsfs", "fsspec"], extras="gcs")
    async def run_async(self, path: Path, file_data: FileData, **kwargs: Any) -> None:
        return await super().run_async(path=path, file_data=file_data, **kwargs)


add_source_entry(
    source_type=CONNECTOR_TYPE,
    entry=SourceRegistryEntry(
        indexer=GcsIndexer,
        indexer_config=GcsIndexerConfig,
        downloader=GcsDownloader,
        downloader_config=GcsDownloaderConfig,
        connection_config=GcsConnectionConfig,
    ),
)

add_destination_entry(
    destination_type=CONNECTOR_TYPE,
    entry=DestinationRegistryEntry(
        uploader=GcsUploader,
        uploader_config=GcsUploaderConfig,
        connection_config=GcsConnectionConfig,
    ),
)
