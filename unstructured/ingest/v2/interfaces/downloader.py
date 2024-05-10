from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, TypeVar

from unstructured.ingest.v2.interfaces.connector import BaseConnector
from unstructured.ingest.v2.interfaces.file_data import FileData
from unstructured.ingest.v2.interfaces.process import BaseProcess


@dataclass
class BaseDownloaderConfig:
    pass


config_type = TypeVar("config_type", bound=BaseDownloaderConfig)


@dataclass
class Downloader(BaseProcess, BaseConnector, ABC):
    download_config: Optional[config_type] = None

    def is_async(self) -> bool:
        return True

    @abstractmethod
    def run(self, file_data: FileData, **kwargs) -> Path:
        pass

    async def run_async(self, file_data: FileData, **kwargs) -> Path:
        return self.run(**kwargs)
