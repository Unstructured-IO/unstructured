import os
from dataclasses import dataclass
from pathlib import Path
from typing import Type
from urllib.parse import urlparse

from unstructured.ingest.connector.fsspec import (
    FsspecIngestDoc,
    FsspecSourceConnector,
    SimpleFsspecConfig,
)
from unstructured.ingest.error import SourceConnectionError
from unstructured.utils import requires_dependencies


@dataclass
class SimpleSftpConfig(SimpleFsspecConfig):
    host: str = ""
    port: int = 22

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
        self.host = parsed_url.hostname
        self.port = parsed_url.port or self.port


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

    def __post_init__(self):
        self.ingest_doc_cls: Type[SftpIngestDoc] = SftpIngestDoc
