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

CONNECTOR_TYPE = "sftp"


@dataclass
class SftpIndexerConfig(FsspecIndexerConfig):
    pass


@dataclass
class SftpAccessConfig(FsspecAccessConfig):
    password: str


@dataclass
class SftpConnectionConfig(FsspecConnectionConfig):
    supported_protocols: list[str] = field(default_factory=lambda: ["sftp"])
    access_config: SftpAccessConfig = enhanced_field(sensitive=True)
    connector_type: str = CONNECTOR_TYPE
    host: str = ""
    port: int = 22
    look_for_keys: bool = False
    allow_agent: bool = False

    def get_access_config(self) -> dict[str, Any]:
        access_config = {
            "host": self.host,
            "port": self.port,
            "look_for_keys": self.look_for_keys,
            "allow_agent": self.allow_agent,
            "password": self.access_config.password,
        }
        return access_config


@dataclass
class SftpIndexer(FsspecIndexer):
    connection_config: SftpConnectionConfig
    index_config: SftpIndexerConfig
    connector_type: str = CONNECTOR_TYPE

    @requires_dependencies(["paramiko", "fsspec"], extras="sftp")
    def __post_init__(self):
        super().__post_init__()

    @requires_dependencies(["paramiko", "fsspec"], extras="sftp")
    def run(self, **kwargs: Any) -> Generator[FileData, None, None]:
        return super().run(**kwargs)


@dataclass
class SftpDownloaderConfig(FsspecDownloaderConfig):
    pass


@dataclass
class SftpDownloader(FsspecDownloader):
    protocol: str = "sftp"
    connection_config: SftpConnectionConfig
    connector_type: str = CONNECTOR_TYPE
    download_config: Optional[SftpDownloaderConfig] = field(default_factory=SftpDownloaderConfig)

    @requires_dependencies(["paramiko", "fsspec"], extras="sftp")
    def __post_init__(self):
        super().__post_init__()

    @requires_dependencies(["paramiko", "fsspec"], extras="sftp")
    def run(self, file_data: FileData, **kwargs: Any) -> Path:
        return super().run(file_data=file_data, **kwargs)

    @requires_dependencies(["paramiko", "fsspec"], extras="sftp")
    async def run_async(self, file_data: FileData, **kwargs: Any) -> Path:
        return await super().run_async(file_data=file_data, **kwargs)


@dataclass
class SftpUploaderConfig(FsspecUploaderConfig):
    pass


@dataclass
class SftpUploader(FsspecUploader):
    connection_config: SftpConnectionConfig
    upload_config: SftpUploaderConfig = field(default=None)

    @requires_dependencies(["paramiko", "fsspec"], extras="sftp")
    def __post_init__(self):
        super().__post_init__()

    @requires_dependencies(["paramiko", "fsspec"], extras="sftp")
    def run(self, contents: list[UploadContent], **kwargs: Any) -> None:
        return super().run(contents=contents, **kwargs)

    @requires_dependencies(["paramiko", "fsspec"], extras="sftp")
    async def run_async(self, path: Path, file_data: FileData, **kwargs: Any) -> None:
        return await super().run_async(path=path, file_data=file_data, **kwargs)


add_source_entry(
    source_type=CONNECTOR_TYPE,
    entry=SourceRegistryEntry(
        indexer=SftpIndexer,
        indexer_config=SftpIndexerConfig,
        downloader=SftpDownloader,
        downloader_config=SftpDownloaderConfig,
        connection_config=SftpConnectionConfig,
    ),
)

add_destination_entry(
    destination_type=CONNECTOR_TYPE,
    entry=DestinationRegistryEntry(
        uploader=SftpUploader,
        uploader_config=SftpUploaderConfig,
        connection_config=SftpConnectionConfig,
    ),
)
