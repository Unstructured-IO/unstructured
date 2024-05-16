import fnmatch
import json
import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from time import time
from typing import TYPE_CHECKING, Any, Generator, Optional

from unstructured.documents.elements import DataSourceMetadata
from unstructured.ingest.enhanced_dataclass import enhanced_field
from unstructured.ingest.error import SourceConnectionError, SourceConnectionNetworkError
from unstructured.ingest.v2.interfaces import (
    AccessConfig,
    ConnectionConfig,
    Downloader,
    DownloaderConfig,
    FileData,
    Indexer,
    IndexerConfig,
    SourceIdentifiers,
    UploadContent,
    Uploader,
    UploaderConfig,
)
from unstructured.ingest.v2.logger import logger

if TYPE_CHECKING:
    from fsspec import AbstractFileSystem

CONNECTOR_TYPE = "fsspec"


class Base(object):
    def __post_init__(self):
        pass


@dataclass
class FileConfig(Base):
    remote_url: str
    protocol: str = field(init=False)
    path_without_protocol: str = field(init=False)
    supported_protocols: list[str] = field(
        default_factory=lambda: [
            "s3",
            "s3a",
            "abfs",
            "az",
            "gs",
            "gcs",
            "box",
            "dropbox",
            "sftp",
        ]
    )

    def __post_init__(self):
        super().__post_init__()
        self.protocol, self.path_without_protocol = self.remote_url.split("://")
        if self.protocol not in self.supported_protocols:
            raise ValueError(
                "Protocol {} not supported yet, only {} are supported.".format(
                    self.protocol, ", ".join(self.supported_protocols)
                ),
            )


class FsspecIndexerConfig(FileConfig, IndexerConfig):
    recursive: bool = False
    file_glob: Optional[list[str]] = None


@dataclass
class FsspecAccessConfig(AccessConfig):
    pass


class FsspecConnectionConfig(ConnectionConfig):
    access_config: FsspecAccessConfig = enhanced_field(sensitive=True, default=None)
    connector_type: str = CONNECTOR_TYPE


def convert_datetime(data: dict) -> dict:
    def json_serial(obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        raise TypeError("Type %s not serializable" % type(obj))

    data_s = json.dumps(data, default=json_serial)
    return json.loads(data_s)


@dataclass
class FsspecIndexer(Indexer):
    connection_config: FsspecConnectionConfig
    index_config: FsspecIndexerConfig = field(default_factory=FsspecIndexerConfig)
    connector_type: str = CONNECTOR_TYPE
    fs: "AbstractFileSystem" = field(init=False)

    def __post_init__(self):
        from fsspec import AbstractFileSystem, get_filesystem_class

        self.fs: AbstractFileSystem = get_filesystem_class(self.index_config.protocol)(
            **self.connection_config.get_access_config(),
        )

    def does_path_match_glob(self, path: str) -> bool:
        if self.index_config.file_glob is None:
            return True
        patterns = self.index_config.file_glob
        for pattern in patterns:
            if fnmatch.filter([path], pattern):
                return True
        logger.debug(f"The file {path!r} is discarded as it does not match any given glob.")
        return False

    def check_connection(self):
        from fsspec import get_filesystem_class

        try:
            fs = get_filesystem_class(self.index_config.protocol)(
                **self.connection_config.get_access_config(),
            )
            fs.ls(path=self.index_config.path_without_protocol, detail=False)
        except Exception as e:
            logger.error(f"failed to validate connection: {e}", exc_info=True)
            raise SourceConnectionError(f"failed to validate connection: {e}")

    def list_files(self):
        if not self.index_config.recursive:
            # fs.ls does not walk directories
            # directories that are listed in cloud storage can cause problems
            # because they are seen as 0 byte files
            return [
                x.get("name")
                for x in self.fs.ls(self.index_config.path_without_protocol, detail=True)
                if x.get("size") > 0
            ]
        else:
            # fs.find will recursively walk directories
            # "size" is a common key for all the cloud protocols with fs
            return [
                k
                for k, v in self.fs.find(
                    self.index_config.path_without_protocol,
                    detail=True,
                ).items()
                if v.get("size") > 0
            ]

    def get_metadata(self, path) -> DataSourceMetadata:
        date_created = None
        date_modified = None

        try:
            created: Optional[Any] = self.fs.created(path)
            if created:
                if isinstance(created, datetime):
                    date_created = str(created.timestamp())
                else:
                    date_created = str(created)
        except NotImplementedError:
            pass

        try:
            modified: Optional[Any] = self.fs.modified(path)
            if modified:
                if isinstance(modified, datetime):
                    date_modified = str(modified.timestamp())
                else:
                    date_modified = str(modified)
        except NotImplementedError:
            pass

        version = self.fs.checksum(path)
        return DataSourceMetadata(
            date_created=date_created,
            date_modified=date_modified,
            date_processed=str(time()),
            version=str(version),
            url=f"{self.index_config.protocol}://{path}",
            record_locator={
                "protocol": self.index_config.protocol,
                "remote_file_path": self.index_config.remote_url,
            },
        )

    def run(self, **kwargs) -> Generator[FileData, None, None]:
        raw_files = self.list_files()
        files = [f for f in raw_files if self.does_path_match_glob(f)]
        for file in files:
            yield FileData(
                identifier=file,
                connector_type=self.connector_type,
                source_identifiers=SourceIdentifiers(
                    filename=Path(file).name,
                    rel_path=file.replace(self.index_config.path_without_protocol, ""),
                    fullpath=file,
                    additional_metadata=convert_datetime(self.fs.info(path=file)),
                ),
                metadata=self.get_metadata(path=file),
            )


class FsspecDownloaderConfig(DownloaderConfig):
    pass


class FsspecDownloader(Downloader):
    protocol: str
    connection_config: FsspecConnectionConfig
    connector_type: str = CONNECTOR_TYPE
    download_config: Optional[FsspecDownloaderConfig] = field(
        default_factory=FsspecDownloaderConfig
    )
    fs: "AbstractFileSystem" = field(init=False)

    def __post_init__(self):
        from fsspec import AbstractFileSystem, get_filesystem_class

        self.fs: AbstractFileSystem = get_filesystem_class(self.protocol)(
            **self.connection_config.get_access_config(),
        )

    def get_download_path(self, file_data: FileData) -> Path:
        return self.download_config.download_dir / Path(file_data.source_identifiers.rel_path)

    @staticmethod
    def is_float(value: str):
        try:
            float(value)
            return True
        except ValueError:
            return False

    def run(self, file_data: FileData, **kwargs) -> Path:
        download_path = self.get_download_path(file_data=file_data)
        try:
            self.fs.get(rpath=file_data.identifier, lpath=download_path.as_posix())
        except Exception as e:
            logger.error(f"failed to download file {file_data.identifier}: {e}", exc_info=True)
            raise SourceConnectionNetworkError(f"failed to download file {file_data.identifier}")
        if (
            file_data.metadata.date_modified
            and self.is_float(file_data.metadata.date_modified)
            and file_data.metadata.date_created
            and self.is_float(file_data.metadata.date_created)
        ):
            date_modified = float(file_data.metadata.date_modified)
            date_created = float(file_data.metadata.date_created)
            os.utime(download_path, times=(date_created, date_modified))
        return download_path


@dataclass
class FsspecUploaderConfig(FileConfig, UploaderConfig):
    overwrite: bool = False


@dataclass
class FsspecUploader(Uploader):
    upload_config: FsspecUploaderConfig = field(default_factory=FsspecUploaderConfig)
    fs: "AbstractFileSystem" = field(init=False)

    def is_async(self) -> bool:
        return True

    def __post_init__(self):
        from fsspec import AbstractFileSystem, get_filesystem_class

        self.fs: AbstractFileSystem = get_filesystem_class(self.upload_config.protocol)(
            **self.connection_config.get_access_config(),
        )

    def run(self, contents: list[UploadContent], **kwargs):
        raise NotImplementedError

    async def run_async(self, path: Path, file_data: FileData, **kwargs):
        upload_path = (
            Path(self.upload_config.path_without_protocol) / file_data.source_identifiers.rel_path
        )
        if self.fs.exists(path=upload_path) and not self.upload_config.overwrite:
            logger.debug(f"Skipping upload of {path} to {upload_path}, file already exists")
            return
        logger.info(f"Writing local file {path} to {upload_path}")
        self.fs.upload(lpath=path, rpath=upload_path)
