import glob
import itertools
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from time import time
from typing import Generator, Optional

from unstructured.documents.elements import DataSourceMetadata
from unstructured.ingest.v2.interfaces import (
    BaseDownloaderConfig,
    BaseIndexerConfig,
    BaseUploaderConfig,
    Destination,
    Downloader,
    FileData,
    Indexer,
    Source,
    SourceIdentifiers,
    UploadContent,
    Uploader,
)
from unstructured.ingest.v2.logging import logger

CONNECTOR_TYPE = "local"


@dataclass
class LocalIndexerConfig(BaseIndexerConfig):
    input_path: Path
    recursive: bool = False
    file_glob: Optional[list[str]] = None


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


class LocalDownloaderConfig(BaseDownloaderConfig):
    pass


class LocalDownloader(Downloader):
    download_config: Optional[LocalDownloaderConfig] = None

    def run(self, file_data: FileData, **kwargs) -> Path:
        return Path(file_data.source_identifiers)


@dataclass(kw_only=True)
class LocalSource(Source):
    indexer: LocalIndexer
    downloader: LocalDownloader = field(default_factory=LocalDownloader)
    connector_type: str = CONNECTOR_TYPE

    def check_connection(self):
        if not self.indexer.index_config.input_path.exists():
            raise ValueError("path to process does not exist")


@dataclass
class LocalUploaderConfig(BaseUploaderConfig):
    output_path: Path


@dataclass
class LocalUploader(Uploader):
    upload_config: LocalUploaderConfig

    def is_async(self) -> bool:
        return False

    def run(self, contents: list[UploadContent], **kwargs):
        self.upload_config.output_path.parent.mkdir(parents=True, exist_ok=True)
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
