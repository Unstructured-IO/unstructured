import glob
import itertools
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from time import time
from typing import Generator, Optional

from unstructured.documents.elements import DataSourceMetadata
from unstructured.ingest.v2.interfaces import (
    Destination,
    Downloader,
    DownloaderConfig,
    FileData,
    Indexer,
    IndexerConfig,
    Source,
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
class LocalIndexerConfig(IndexerConfig):
    input_filepath: str
    recursive: bool = False
    file_glob: Optional[list[str]] = None

    @property
    def input_path(self) -> Path:
        return Path(self.input_filepath).resolve()


@dataclass
class LocalIndexer(Indexer):
    index_config: LocalIndexerConfig

    def list_files(self) -> list[Path]:
        input_path = self.index_config.input_path
        if input_path.is_file():
            return [Path(s) for s in glob.glob(f"{self.index_config.input_path}")]
        glob_fn = input_path.rglob if self.index_config.recursive else input_path.glob
        if not self.index_config.file_glob:
            return list(glob_fn("*"))
        return list(
            itertools.chain.from_iterable(
                glob_fn(pattern) for pattern in self.index_config.file_glob
            )
        )

    def get_file_metadata(self, path: Path) -> DataSourceMetadata:
        return DataSourceMetadata(
            date_modified=str(path.stat().st_mtime) or None,
            date_created=str(path.stat().st_birthtime) or None,
            date_processed=str(time()),
            permissions_data=[{"mode": path.stat().st_mode}],
            record_locator={"path": str(path.resolve())},
        )

    def run(self, **kwargs) -> Generator[FileData, None, None]:
        for file_path in self.list_files():
            file_data = FileData(
                identifier=str(file_path.resolve()),
                connector_type=CONNECTOR_TYPE,
                source_identifiers=SourceIdentifiers(
                    fullpath=str(file_path.resolve()),
                    filename=file_path.name,
                    rel_path=str(file_path.resolve()).replace(
                        str(self.index_config.input_path.resolve()), ""
                    )[1:],
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
    download_config: Optional[LocalDownloaderConfig] = None

    def get_download_path(self, file_data: FileData) -> Path:
        return Path(file_data.source_identifiers.fullpath)

    def run(self, file_data: FileData, **kwargs) -> Path:
        return Path(file_data.source_identifiers.fullpath)


@dataclass(kw_only=True)
class LocalSource(Source):
    indexer: LocalIndexer
    downloader: LocalDownloader = field(default_factory=LocalDownloader)
    connector_type: str = CONNECTOR_TYPE

    def check_connection(self):
        if not self.indexer.index_config.input_path.exists():
            raise ValueError("path to process does not exist")


@dataclass
class LocalUploaderConfig(UploaderConfig):
    output_directory: str = field(default="structured-output")

    @property
    def output_path(self) -> Path:
        return Path(self.output_directory).resolve()

    def __post_init__(self):
        if self.output_path.exists() and self.output_path.is_file():
            raise ValueError("output path already exists as a file")


@dataclass
class LocalUploader(Uploader):
    upload_config: LocalUploaderConfig = field(default_factory=LocalUploaderConfig)

    def is_async(self) -> bool:
        return False

    def run(self, contents: list[UploadContent], **kwargs):
        self.upload_config.output_path.mkdir(parents=True, exist_ok=True)
        for content in contents:
            identifiers = content.file_data.source_identifiers
            new_path = self.upload_config.output_path / identifiers.relative_path
            final_path = str(new_path).replace(
                identifiers.filename, f"{identifiers.filename_stem}.json"
            )
            logger.debug(f"copying file from {content.path} to {final_path}")
            shutil.copy(src=str(content.path), dst=str(final_path))


@dataclass(kw_only=True)
class LocalDestination(Destination):
    uploader: LocalUploader
    connector_type: str = CONNECTOR_TYPE

    def check_connection(self):
        if not self.uploader.upload_config.output_path.is_file():
            raise ValueError(
                f"input path points to an existing file: {self.uploader.upload_config.output_path}"
            )


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
