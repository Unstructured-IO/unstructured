import os
from dataclasses import dataclass
from pathlib import Path
from typing import Type
from urllib.parse import urlparse

from unstructured.ingest.connector.fsspec.fsspec import (
    FsspecIngestDoc,
    FsspecSourceConnector,
    SimpleFsspecConfig,
)
from unstructured.ingest.enhanced_dataclass import enhanced_field
from unstructured.ingest.error import SourceConnectionError
from unstructured.ingest.interfaces import AccessConfig
from unstructured.ingest.logger import logger
from unstructured.utils import requires_dependencies


@dataclass
class SftpAccessConfig(AccessConfig):
    username: str
    password: str = enhanced_field(sensitive=True)
    host: str = ""
    port: int = 22


@dataclass
class SimpleSftpConfig(SimpleFsspecConfig):
    access_config: SftpAccessConfig = None

    def __post_init__(self):
        super().__post_init__()

        _, ext = os.path.splitext(self.remote_url)
        parsed_url = urlparse(self.remote_url)
        if ext:
            # We only want the file_path if it has an extension
            self.file_path = Path(self.remote_url).name
            self.dir_path = Path(parsed_url.path).parent.as_posix().lstrip("/")
            self.path_without_protocol = self.dir_path
        else:
            self.file_path = ""
            self.dir_path = parsed_url.path.lstrip("/")
            self.path_without_protocol = self.dir_path
        self.access_config.host = parsed_url.hostname or self.access_config.host
        self.access_config.port = parsed_url.port or self.access_config.port


@dataclass
class SftpIngestDoc(FsspecIngestDoc):
    connector_config: SimpleSftpConfig
    registry_name: str = "sftp"

    @SourceConnectionError.wrap
    @requires_dependencies(["paramiko", "fsspec"], extras="sftp")
    def get_file(self):
        super().get_file()


@dataclass
class SftpSourceConnector(FsspecSourceConnector):
    connector_config: SimpleSftpConfig

    @requires_dependencies(["paramiko", "fsspec"], extras="sftp")
    def initialize(self):
        super().initialize()

    @requires_dependencies(["paramiko", "fsspec"], extras="sftp")
    def check_connection(self):
        from fsspec.implementations.sftp import SFTPFileSystem

        try:
            SFTPFileSystem(**self.connector_config.get_access_config())
        except Exception as e:
            logger.error(f"failed to validate connection: {e}", exc_info=True)
            raise SourceConnectionError(f"failed to validate connection: {e}")

    def __post_init__(self):
        self.ingest_doc_cls: Type[SftpIngestDoc] = SftpIngestDoc
