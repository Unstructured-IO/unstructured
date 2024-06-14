from __future__ import annotations

import fnmatch
import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from time import time
from typing import TYPE_CHECKING, Any, Generator, Optional, TypeVar

from unstructured.documents.elements import DataSourceMetadata
from unstructured.ingest.enhanced_dataclass import enhanced_field
from unstructured.ingest.error import SourceConnectionError, SourceConnectionNetworkError
from unstructured.ingest.v2.interfaces import (
    AccessConfig,
    ConnectionConfig,
    Downloader,
    DownloaderConfig,
    DownloadResponse,
    FileData,
    Indexer,
    IndexerConfig,
    SourceIdentifiers,
    UploadContent,
    Uploader,
    UploaderConfig,
)
from unstructured.ingest.v2.logger import logger
from unstructured.ingest.v2.processes.connectors.fsspec.utils import sterilize_dict

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


@dataclass
class FsspecIndexerConfig(FileConfig, IndexerConfig):
    recursive: bool = False
    file_glob: Optional[list[str]] = None


@dataclass
class FsspecAccessConfig(AccessConfig):
    pass


FsspecAccessConfigT = TypeVar("FsspecAccessConfigT", bound=FsspecAccessConfig)


class FsspecConnectionConfig(ConnectionConfig):
    access_config: FsspecAccessConfigT = enhanced_field(sensitive=True, default=None)
    connector_type: str = CONNECTOR_TYPE


FsspecIndexerConfigT = TypeVar("FsspecIndexerConfigT", bound=FsspecIndexerConfig)
FsspecConnectionConfigT = TypeVar("FsspecConnectionConfigT", bound=FsspecConnectionConfig)


@dataclass
class FsspecIndexer(Indexer):
    connection_config: FsspecConnectionConfigT
    index_config: FsspecIndexerConfigT
    connector_type: str = CONNECTOR_TYPE
    fs: "AbstractFileSystem" = field(init=False)

    def __post_init__(self):
        from fsspec import get_filesystem_class

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

    def list_files(self) -> list[str]:
        if not self.index_config.recursive:
            # fs.ls does not walk directories
            # directories that are listed in cloud storage can cause problems
            # because they are seen as 0 byte files
            found = self.fs.ls(self.index_config.path_without_protocol, detail=True)
            if isinstance(found, list):
                return [
                    x.get("name") for x in found if x.get("size") > 0 and x.get("type") == "file"
                ]
            else:
                raise TypeError(f"unhandled response type from ls: {type(found)}")
        else:
            # fs.find will recursively walk directories
            # "size" is a common key for all the cloud protocols with fs
            found = self.fs.find(
                self.index_config.path_without_protocol,
                detail=True,
            )
            if isinstance(found, dict):
                return [
                    k for k, v in found.items() if v.get("size") > 0 and v.get("type") == "file"
                ]
            else:
                raise TypeError(f"unhandled response type from find: {type(found)}")

    def get_metadata(self, path: str) -> DataSourceMetadata:
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

    def sterilize_info(self, path) -> dict:
        info = self.fs.info(path=path)
        return sterilize_dict(data=info)

    def run(self, **kwargs: Any) -> Generator[FileData, None, None]:
        raw_files = self.list_files()
        files = [f for f in raw_files if self.does_path_match_glob(f)]
        for file in files:
            # Note: we remove any remaining leading slashes (Box introduces these)
            # to get a valid relative path
            rel_path = file.replace(self.index_config.path_without_protocol, "").lstrip("/")
            yield FileData(
                identifier=file,
                connector_type=self.connector_type,
                source_identifiers=SourceIdentifiers(
                    filename=Path(file).name,
                    rel_path=rel_path or None,
                    fullpath=file,
                ),
                metadata=self.get_metadata(path=file),
                additional_metadata=self.sterilize_info(path=file),
            )


class FsspecDownloaderConfig(DownloaderConfig):
    pass


FsspecDownloaderConfigT = TypeVar("FsspecDownloaderConfigT", bound=FsspecDownloaderConfig)


class FsspecDownloader(Downloader):
    protocol: str
    connection_config: FsspecConnectionConfigT
    connector_type: str = CONNECTOR_TYPE
    download_config: Optional[FsspecDownloaderConfigT] = field(
        default_factory=lambda: FsspecDownloaderConfig()
    )
    fs: "AbstractFileSystem" = field(init=False)

    def __post_init__(self):
        from fsspec import get_filesystem_class

        self.fs: AbstractFileSystem = get_filesystem_class(self.protocol)(
            **self.connection_config.get_access_config(),
        )

    def get_download_path(self, file_data: FileData) -> Path:
        return (
            self.download_config.download_dir / Path(file_data.source_identifiers.relative_path)
            if self.download_config
            else Path(file_data.source_identifiers.rel_path)
        )

    @staticmethod
    def is_float(value: str):
        try:
            float(value)
            return True
        except ValueError:
            return False

    def run(self, file_data: FileData, **kwargs: Any) -> DownloadResponse:
        download_path = self.get_download_path(file_data=file_data)
        download_path.parent.mkdir(parents=True, exist_ok=True)
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
        return DownloadResponse(file_data=file_data, path=download_path)


@dataclass
class FsspecUploaderConfig(FileConfig, UploaderConfig):
    overwrite: bool = False


FsspecUploaderConfigT = TypeVar("FsspecUploaderConfigT", bound=FsspecUploaderConfig)


@dataclass
class FsspecUploader(Uploader):
    upload_config: FsspecUploaderConfigT = field(default=None)
    fs: "AbstractFileSystem" = field(init=False)

    def is_async(self) -> bool:
        return True

    def __post_init__(self):
        # TODO once python3.9 no longer supported and kw_only is allowed in dataclasses, remove:
        if not self.upload_config:
            raise TypeError(
                f"{self.__class__.__name__}.__init__() "
                f"missing 1 required positional argument: 'upload_config'"
            )

        from fsspec import get_filesystem_class

        fs_kwargs = self.connection_config.get_access_config() if self.connection_config else {}
        self.fs: AbstractFileSystem = get_filesystem_class(self.upload_config.protocol)(
            **fs_kwargs,
        )

    def run(self, contents: list[UploadContent], **kwargs: Any) -> None:
        raise NotImplementedError

    async def run_async(self, path: Path, file_data: FileData, **kwargs: Any) -> None:
        upload_path = (
            Path(self.upload_config.path_without_protocol)
            / file_data.source_identifiers.relative_path
        )
        updated_upload_path = upload_path.parent / f"{upload_path.name}.json"
        upload_path_str = str(updated_upload_path)
        path_str = str(path.resolve())
        if self.fs.exists(path=upload_path_str) and not self.upload_config.overwrite:
            logger.debug(f"Skipping upload of {path} to {upload_path}, file already exists")
            return
        logger.info(f"Writing local file {path_str} to {upload_path}")
        self.fs.upload(lpath=path_str, rpath=upload_path_str)
