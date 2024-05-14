from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import TypeVar

from unstructured.ingest.v2.interfaces.connector import BaseConnector
from unstructured.ingest.v2.interfaces.file_data import FileData
from unstructured.ingest.v2.interfaces.process import BaseProcess


@dataclass
class UploaderConfig:
    pass


config_type = TypeVar("config_type", bound=UploaderConfig)


@dataclass
class UploadContent:
    path: Path
    file_data: FileData


@dataclass
class Uploader(BaseProcess, BaseConnector, ABC):
    upload_config: config_type = field(default_factory=UploaderConfig)

    def is_async(self) -> bool:
        return False

    @abstractmethod
    def run(self, contents: list[UploadContent], **kwargs):
        pass

    async def run_async(self, path: Path, file_data: FileData, **kwargs):
        return self.run(contents=[UploadContent(path=path, file_data=file_data)], **kwargs)
