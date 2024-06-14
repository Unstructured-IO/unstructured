import glob
import itertools
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from time import time
from typing import Any, Generator, Optional

from unstructured.documents.elements import DataSourceMetadata
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
from unstructured.ingest.v2.processes.connector_registry import (
    DestinationRegistryEntry,
    SourceRegistryEntry,
    add_destination_entry,
    add_source_entry,
)

CONNECTOR_TYPE = "local"


@dataclass
class LocalAccessConfig(AccessConfig):
    pass


@dataclass
class LocalConnectionConfig(ConnectionConfig):
    access_config: LocalAccessConfig = field(default_factory=lambda: LocalAccessConfig())


@dataclass
class LocalIndexerConfig(IndexerConfig):
    input_path: str
    recursive: bool = False
    file_glob: Optional[list[str]] = None

    @property
    def path(self) -> Path:
        return Path(self.input_path).resolve()


@dataclass
class LocalIndexer(Indexer):
    index_config: LocalIndexerConfig
    connection_config: LocalConnectionConfig = field(
        default_factory=lambda: LocalConnectionConfig()
    )
    connector_type: str = CONNECTOR_TYPE

    def list_files(self) -> list[Path]:
        input_path = self.index_config.path
        if input_path.is_file():
            return [Path(s) for s in glob.glob(f"{self.index_config.path}")]
        glob_fn = input_path.rglob if self.index_config.recursive else input_path.glob
        if not self.index_config.file_glob:
            return list(glob_fn("*"))
        return list(
            itertools.chain.from_iterable(
                glob_fn(pattern) for pattern in self.index_config.file_glob
            )
        )

    def get_file_metadata(self, path: Path) -> DataSourceMetadata:
        stats = path.stat()
        try:
            date_modified = str(stats.st_mtime)
        except Exception as e:
            logger.warning(f"Couldn't detect date modified: {e}")
            date_modified = None

        try:
            date_created = str(stats.st_birthtime)
        except Exception as e:
            logger.warning(f"Couldn't detect date created: {e}")
            date_created = None

        try:
            mode = stats.st_mode
            permissions_data = [{"mode": mode}]
        except Exception as e:
            logger.warning(f"Couldn't detect file mode: {e}")
            permissions_data = None
        return DataSourceMetadata(
            date_modified=date_modified,
            date_created=date_created,
            date_processed=str(time()),
            permissions_data=permissions_data,
            record_locator={"path": str(path.resolve())},
        )

    def run(self, **kwargs: Any) -> Generator[FileData, None, None]:
        for file_path in self.list_files():
            file_data = FileData(
                identifier=str(file_path.resolve()),
                connector_type=CONNECTOR_TYPE,
                source_identifiers=SourceIdentifiers(
                    fullpath=str(file_path.resolve()),
                    filename=file_path.name,
                    rel_path=(
                        str(file_path.resolve()).replace(str(self.index_config.path.resolve()), "")[
                            1:
                        ]
                        if not self.index_config.path.is_file()
                        else self.index_config.path.name
                    ),
                ),
                metadata=self.get_file_metadata(path=file_path),
            )
            yield file_data


@dataclass
class LocalDownloaderConfig(DownloaderConfig):
    pass


@dataclass
class LocalDownloader(Downloader):
    connector_type: str = CONNECTOR_TYPE
    connection_config: LocalConnectionConfig = field(
        default_factory=lambda: LocalConnectionConfig()
    )
    download_config: LocalDownloaderConfig = field(default_factory=lambda: LocalDownloaderConfig())

    def get_download_path(self, file_data: FileData) -> Path:
        return Path(file_data.source_identifiers.fullpath)

    def run(self, file_data: FileData, **kwargs: Any) -> DownloadResponse:
        return DownloadResponse(
            file_data=file_data, path=Path(file_data.source_identifiers.fullpath)
        )


@dataclass
class LocalUploaderConfig(UploaderConfig):
    output_dir: str = field(default="structured-output")

    @property
    def output_path(self) -> Path:
        return Path(self.output_dir).resolve()

    def __post_init__(self):
        if self.output_path.exists() and self.output_path.is_file():
            raise ValueError("output path already exists as a file")


@dataclass
class LocalUploader(Uploader):
    upload_config: LocalUploaderConfig = field(default_factory=lambda: LocalUploaderConfig())
    connection_config: LocalConnectionConfig = field(
        default_factory=lambda: LocalConnectionConfig()
    )

    def is_async(self) -> bool:
        return False

    def run(self, contents: list[UploadContent], **kwargs: Any) -> None:
        self.upload_config.output_path.mkdir(parents=True, exist_ok=True)
        for content in contents:
            if source_identifiers := content.file_data.source_identifiers:
                identifiers = source_identifiers
                new_path = self.upload_config.output_path / identifiers.relative_path
                final_path = str(new_path).replace(
                    identifiers.filename, f"{identifiers.filename}.json"
                )
            else:
                final_path = self.upload_config.output_path / Path(
                    f"{content.file_data.identifier}.json"
                )
            Path(final_path).parent.mkdir(parents=True, exist_ok=True)
            logger.debug(f"copying file from {content.path} to {final_path}")
            shutil.copy(src=str(content.path), dst=str(final_path))


add_source_entry(
    source_type=CONNECTOR_TYPE,
    entry=SourceRegistryEntry(
        indexer=LocalIndexer,
        indexer_config=LocalIndexerConfig,
        downloader=LocalDownloader,
        downloader_config=LocalDownloaderConfig,
    ),
)

add_destination_entry(
    destination_type=CONNECTOR_TYPE,
    entry=DestinationRegistryEntry(uploader=LocalUploader, uploader_config=LocalUploaderConfig),
)
