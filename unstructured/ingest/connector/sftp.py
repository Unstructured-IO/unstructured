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
    def __post_init__(self):
        # host: t.Optional[str] = ""
        # port: t.Optional[str] = ""
        super().__post_init__()
        print("****** SimpleSftpConfig *****")
        print(self.protocol)
        print(self.access_kwargs)
        # breakpoint()
        print("*************")

        _,ext= os.path.splitext(self.remote_url)
        if ext:
            # then we can know there is a file
            self.file_path= Path(self.remote_url).name
            rr=Path(self.remote_url).parent.as_posix()
        else:
            rr=self.remote_url

            
        uu= urlparse(rr)
        breakpoint()
        self.path_without_protocol = uu.path.lstrip("/") #Path(u.path).parent
        self.dir_path = uu.path.lstrip("/") #Path(u.path).parent
        self.host= urlparse(self.remote_url).hostname
        self.port= urlparse(self.remote_url).port
        # breakpoint()
        print("*************")


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
