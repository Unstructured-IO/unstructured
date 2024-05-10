from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, TypeVar

from unstructured.ingest.v2.interfaces.connector import BaseConnector
from unstructured.ingest.v2.interfaces.file_data import FileData
from unstructured.ingest.v2.interfaces.process import BaseProcess


@dataclass
class BaseUploaderConfig:
    pass


config_type = TypeVar("config_type", bound=BaseUploaderConfig)


@dataclass
class UploadContent:
    path: Path
    file_data: FileData


@dataclass
class Uploader(BaseProcess, BaseConnector, ABC):
    upload_config: Optional[config_type] = None

    def is_async(self) -> bool:
        return True

    @abstractmethod
    def run(self, contents: list[UploadContent], **kwargs):
        pass

    async def run_async(self, contents: list[UploadContent], **kwargs):
        return self.run(contents=contents, **kwargs)
