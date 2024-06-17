from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Generator, Optional
from urllib.parse import urlparse

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

CONNECTOR_TYPE = "sftp"


@dataclass
class SftpIndexerConfig(FsspecIndexerConfig):
    def __post_init__(self):
        super().__post_init__()
        _, ext = os.path.splitext(self.remote_url)
        parsed_url = urlparse(self.remote_url)
        if ext:
            self.path_without_protocol = Path(parsed_url.path).parent.as_posix().lstrip("/")
        else:
            self.path_without_protocol = parsed_url.path.lstrip("/")


@dataclass
class SftpAccessConfig(FsspecAccessConfig):
    password: str


@dataclass
class SftpConnectionConfig(FsspecConnectionConfig):
    supported_protocols: list[str] = field(default_factory=lambda: ["sftp"])
    access_config: SftpAccessConfig = enhanced_field(sensitive=True)
    connector_type: str = CONNECTOR_TYPE
    username: Optional[str] = None
    host: Optional[str] = None
    port: int = 22
    look_for_keys: bool = False
    allow_agent: bool = False

    def get_access_config(self) -> dict[str, Any]:
        access_config = {
            "username": self.username,
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
        parsed_url = urlparse(self.index_config.remote_url)
        self.connection_config.host = parsed_url.hostname or self.connection_config.host
        self.connection_config.port = parsed_url.port or self.connection_config.port
        super().__post_init__()

    @requires_dependencies(["paramiko", "fsspec"], extras="sftp")
    def run(self, **kwargs: Any) -> Generator[FileData, None, None]:
        for file in super().run(**kwargs):
            new_identifier = (
                f"sftp://"
                f"{self.connection_config.host}:"
                f"{self.connection_config.port}/"
                f"{file.identifier}"
            )
            file.identifier = new_identifier
            yield file


@dataclass
class SftpDownloaderConfig(FsspecDownloaderConfig):
    remote_url: Optional[str] = None

    def __post_init__(self):
        # TODO once python3.9 no longer supported and kw_only is allowed in dataclasses, remove:
        if not self.remote_url:
            raise TypeError(
                f"{self.__class__.__name__}.__init__() "
                f"missing 1 required positional argument: 'remote_url'"
            )


@dataclass
class SftpDownloader(FsspecDownloader):
    protocol: str = "sftp"
    connection_config: SftpConnectionConfig
    connector_type: str = CONNECTOR_TYPE
    download_config: Optional[SftpDownloaderConfig] = field(default_factory=SftpDownloaderConfig)

    @requires_dependencies(["paramiko", "fsspec"], extras="sftp")
    def __post_init__(self):
        parsed_url = urlparse(self.download_config.remote_url)
        self.connection_config.host = parsed_url.hostname or self.connection_config.host
        self.connection_config.port = parsed_url.port or self.connection_config.port
        super().__post_init__()

    @requires_dependencies(["paramiko", "fsspec"], extras="sftp")
    def run(self, file_data: FileData, **kwargs: Any) -> DownloadResponse:
        return super().run(file_data=file_data, **kwargs)

    @requires_dependencies(["paramiko", "fsspec"], extras="sftp")
    async def run_async(self, file_data: FileData, **kwargs: Any) -> DownloadResponse:
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
