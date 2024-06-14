from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Generator, Optional

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

CONNECTOR_TYPE = "box"


@dataclass
class BoxIndexerConfig(FsspecIndexerConfig):
    pass


@dataclass
class BoxAccessConfig(FsspecAccessConfig):
    box_app_config: Optional[str] = None


@dataclass
class BoxConnectionConfig(FsspecConnectionConfig):
    supported_protocols: list[str] = field(default_factory=lambda: ["box"])
    access_config: BoxAccessConfig = enhanced_field(
        sensitive=True, default_factory=lambda: BoxAccessConfig()
    )
    connector_type: str = CONNECTOR_TYPE

    def get_access_config(self) -> dict[str, Any]:
        # Return access_kwargs with oauth. The oauth object can not be stored directly in the config
        # because it is not serializable.
        from boxsdk import JWTAuth

        access_kwargs_with_oauth: dict[str, Any] = {
            "oauth": JWTAuth.from_settings_file(
                self.access_config.box_app_config,
            ),
        }
        access_config: dict[str, Any] = self.access_config.to_dict()
        access_config.pop("box_app_config", None)
        access_kwargs_with_oauth.update(access_config)

        return access_kwargs_with_oauth


@dataclass
class BoxIndexer(FsspecIndexer):
    connection_config: BoxConnectionConfig
    index_config: BoxIndexerConfig
    connector_type: str = CONNECTOR_TYPE

    @requires_dependencies(["boxfs"], extras="box")
    def __post_init__(self):
        super().__post_init__()

    @requires_dependencies(["boxfs"], extras="box")
    def run(self, **kwargs: Any) -> Generator[FileData, None, None]:
        return super().run(**kwargs)


@dataclass
class BoxDownloaderConfig(FsspecDownloaderConfig):
    pass


@dataclass
class BoxDownloader(FsspecDownloader):
    protocol: str = "box"
    connection_config: BoxConnectionConfig
    connector_type: str = CONNECTOR_TYPE
    download_config: Optional[BoxDownloaderConfig] = field(default_factory=BoxDownloaderConfig)

    @requires_dependencies(["boxfs"], extras="box")
    def __post_init__(self):
        super().__post_init__()

    @requires_dependencies(["boxfs"], extras="box")
    def run(self, file_data: FileData, **kwargs: Any) -> DownloadResponse:
        return super().run(file_data=file_data, **kwargs)

    @requires_dependencies(["boxfs"], extras="box")
    async def run_async(self, file_data: FileData, **kwargs: Any) -> DownloadResponse:
        return await super().run_async(file_data=file_data, **kwargs)


@dataclass
class BoxUploaderConfig(FsspecUploaderConfig):
    pass


@dataclass
class BoxUpload(FsspecUploader):
    connection_config: BoxConnectionConfig
    upload_config: BoxUploaderConfig = field(default=None)

    @requires_dependencies(["boxfs"], extras="box")
    def __post_init__(self):
        super().__post_init__()

    @requires_dependencies(["boxfs"], extras="box")
    def run(self, contents: list[UploadContent], **kwargs: Any) -> None:
        return super().run(contents=contents, **kwargs)

    @requires_dependencies(["boxfs"], extras="box")
    async def run_async(self, path: Path, file_data: FileData, **kwargs: Any) -> None:
        return await super().run_async(path=path, file_data=file_data, **kwargs)


add_source_entry(
    source_type=CONNECTOR_TYPE,
    entry=SourceRegistryEntry(
        indexer=BoxIndexer,
        indexer_config=BoxIndexerConfig,
        downloader=BoxDownloader,
        downloader_config=BoxDownloaderConfig,
        connection_config=BoxConnectionConfig,
    ),
)

add_destination_entry(
    destination_type=CONNECTOR_TYPE,
    entry=DestinationRegistryEntry(
        uploader=BoxUpload, uploader_config=BoxUploaderConfig, connection_config=BoxConnectionConfig
    ),
)
