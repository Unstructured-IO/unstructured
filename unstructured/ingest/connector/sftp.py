from dataclasses import dataclass
from typing import Type

import typing as t
from urllib.parse import urlparse
from pathlib import Path
import os

from unstructured.ingest.connector.fsspec import (
    FsspecIngestDoc,
    FsspecSourceConnector,
    SimpleFsspecConfig,
)
from unstructured.ingest.error import SourceConnectionError
from unstructured.utils import requires_dependencies


@dataclass
class SimpleSftpConfig(SimpleFsspecConfig):
    host: t.Optional[str] = ""
    port: t.Optional[str] = ""
    def __post_init__(self):
        super().__post_init__()

        _,ext= os.path.splitext(self.remote_url)
        if ext:
            # We only want the filename if it has an extension
            self.file_path= Path(self.remote_url).name
            self.dir_path= Path(urlparse(self.remote_url).path).parent.as_posix().lstrip("/")
            self.path_without_protocol= Path(urlparse(self.remote_url).path).parent.as_posix().lstrip("/")
        else:
            self.file_path=""
            self.dir_path= urlparse(self.remote_url).path.lstrip("/")
            self.path_without_protocol= urlparse(self.remote_url).path.lstrip("/")
        self.host= urlparse(self.remote_url).hostname
        self.port= urlparse(self.remote_url).port


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
