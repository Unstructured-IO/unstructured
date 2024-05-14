from dataclasses import dataclass
from typing import Optional, Type, TypeVar

from unstructured.ingest.v2.interfaces import (
    ConnectionConfig,
    Downloader,
    DownloaderConfig,
    Indexer,
    IndexerConfig,
    Uploader,
    UploaderConfig,
    UploadStager,
    UploadStagerConfig,
)

IndexerT = TypeVar("IndexerT", bound=Indexer)
IndexerConfigT = TypeVar("IndexerConfigT", bound=IndexerConfig)
DownloaderT = TypeVar("DownloaderT", bound=Downloader)
DownloaderConfigT = TypeVar("DownloaderConfigT", bound=DownloaderConfig)
ConnectionConfigT = TypeVar("ConnectionConfigT", bound=ConnectionConfig)
UploadStagerConfigT = TypeVar("UploadStagerConfigT", bound=UploadStagerConfig)
UploadStagerT = TypeVar("UploadStagerT", bound=UploadStager)
UploaderConfigT = TypeVar("UploaderConfigT", bound=UploaderConfig)
UploaderT = TypeVar("UploaderT", bound=Uploader)


@dataclass
class SourceRegistryEntry:
    indexer: Type[IndexerT]
    downloader: Type[DownloaderT]

    downloader_config: Optional[Type[DownloaderConfigT]] = None
    indexer_config: Optional[Type[IndexerConfigT]] = None
    connection_config: Optional[Type[ConnectionConfigT]] = None


source_registry: dict[str, SourceRegistryEntry] = {}


def add_source_entry(source_type: str, entry: SourceRegistryEntry):
    if source_type in source_registry:
        raise ValueError(f"source {source_type} has already been registered")
    source_registry[source_type] = entry


@dataclass
class DestinationRegistryEntry:
    uploader: Type[UploaderT]
    upload_stager: Optional[Type[UploadStagerT]] = None

    upload_stager_config: Optional[Type[UploadStagerConfigT]] = None
    uploader_config: Optional[Type[UploaderConfigT]] = None

    connection_config: Optional[Type[ConnectionConfigT]] = None


destination_registry: dict[str, DestinationRegistryEntry] = {}


def add_destination_entry(destination_type: str, entry: DestinationRegistryEntry):
    if destination_type in destination_registry:
        raise ValueError(f"destination {destination_type} has already been registered")
    destination_registry[destination_type] = entry
