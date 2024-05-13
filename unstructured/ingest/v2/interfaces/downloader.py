from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, TypeVar

from unstructured.ingest.v2.interfaces.connector import BaseConnector
from unstructured.ingest.v2.interfaces.file_data import FileData
from unstructured.ingest.v2.interfaces.process import BaseProcess


@dataclass
class DownloaderConfig:
    download_dir: Optional[Path] = None


config_type = TypeVar("config_type", bound=DownloaderConfig)


@dataclass(kw_only=True)
class Downloader(BaseProcess, BaseConnector, ABC):
    connector_type: str
    download_config: Optional[config_type] = field(default_factory=DownloaderConfig)

    @property
    def download_dir(self) -> Path:
        if self.download_config.download_dir is None:
            self.download_config.download_dir = (
                Path.home()
                / ".cache"
                / "unstructured"
                / "ingest"
                / "download"
                / self.connector_type
            ).resolve()
        return self.download_config.download_dir

    def is_async(self) -> bool:
        return True

    @abstractmethod
    def get_download_path(self, file_data: FileData) -> Path:
        pass

    @abstractmethod
    def run(self, file_data: FileData, **kwargs) -> Path:
        pass

    async def run_async(self, file_data: FileData, **kwargs) -> Path:
        return self.run(file_data=file_data, **kwargs)
