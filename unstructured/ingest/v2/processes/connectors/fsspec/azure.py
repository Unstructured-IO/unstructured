from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Generator, Optional

from unstructured.ingest.enhanced_dataclass import enhanced_field
from unstructured.ingest.v2.interfaces import FileData, UploadContent
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

CONNECTOR_TYPE = "azure"


@dataclass
class AzureIndexerConfig(FsspecIndexerConfig):
    pass


@dataclass
class AzureAccessConfig(FsspecAccessConfig):
    account_name: Optional[str] = None
    account_key: Optional[str] = None
    connection_string: Optional[str] = None
    sas_token: Optional[str] = None


@dataclass
class AzureConnectionConfig(FsspecConnectionConfig):
    supported_protocols: list[str] = field(default_factory=lambda: ["az"])
    access_config: AzureAccessConfig = enhanced_field(
        sensitive=True, default_factory=lambda: AzureAccessConfig()
    )
    connector_type: str = CONNECTOR_TYPE

    def get_access_config(self) -> dict[str, Any]:
        access_configs: dict[str, Any] = self.access_config.to_dict()

        # Avoid injecting None by filtering out k,v pairs where the value is None
        access_configs.update({k: v for k, v in self.access_config.to_dict().items() if v})
        return access_configs


@dataclass
class AzureIndexer(FsspecIndexer):
    connection_config: AzureConnectionConfig
    index_config: AzureIndexerConfig
    connector_type: str = CONNECTOR_TYPE

    @requires_dependencies(["adlfs", "fsspec"], extras="azure")
    def __post_init__(self):
        super().__post_init__()

    @requires_dependencies(["adlfs", "fsspec"], extras="azure")
    def run(self, **kwargs: Any) -> Generator[FileData, None, None]:
        return super().run(**kwargs)


@dataclass
class AzureDownloaderConfig(FsspecDownloaderConfig):
    pass


@dataclass
class AzureDownloader(FsspecDownloader):
    protocol: str = "az"
    connection_config: AzureConnectionConfig
    connector_type: str = CONNECTOR_TYPE
    download_config: Optional[AzureDownloaderConfig] = field(default_factory=AzureDownloaderConfig)

    @requires_dependencies(["adlfs", "fsspec"], extras="azure")
    def __post_init__(self):
        super().__post_init__()

    @requires_dependencies(["adlfs", "fsspec"], extras="azure")
    def run(self, file_data: FileData, **kwargs: Any) -> Path:
        return super().run(file_data=file_data, **kwargs)

    @requires_dependencies(["adlfs", "fsspec"], extras="azure")
    async def run_async(self, file_data: FileData, **kwargs: Any) -> Path:
        return await super().run_async(file_data=file_data, **kwargs)


@dataclass
class AzureUploaderConfig(FsspecUploaderConfig):
    pass


@dataclass
class AzureUpload(FsspecUploader):
    connection_config: AzureConnectionConfig
    upload_config: AzureUploaderConfig = field(default=None)

    @requires_dependencies(["adlfs", "fsspec"], extras="azure")
    def __post_init__(self):
        super().__post_init__()

    @requires_dependencies(["adlfs", "fsspec"], extras="azure")
    def run(self, contents: list[UploadContent], **kwargs: Any) -> None:
        return super().run(contents=contents, **kwargs)

    @requires_dependencies(["adlfs", "fsspec"], extras="azure")
    async def run_async(self, path: Path, file_data: FileData, **kwargs: Any) -> None:
        return await super().run_async(path=path, file_data=file_data, **kwargs)


add_source_entry(
    source_type=CONNECTOR_TYPE,
    entry=SourceRegistryEntry(
        indexer=AzureIndexer,
        indexer_config=AzureIndexerConfig,
        downloader=AzureDownloader,
        downloader_config=AzureDownloaderConfig,
        connection_config=AzureConnectionConfig,
    ),
)

add_destination_entry(
    destination_type=CONNECTOR_TYPE,
    entry=DestinationRegistryEntry(uploader=AzureUpload, uploader_config=AzureUploaderConfig),
)
