from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, TypeVar

from unstructured.ingest.v2.interfaces.file_data import FileData
from unstructured.ingest.v2.interfaces.process import BaseProcess


@dataclass
class UploadStagerConfig:
    pass


config_type = TypeVar("config_type", bound=UploadStagerConfig)


@dataclass
class UploadStager(BaseProcess, ABC):
    upload_stager_config: Optional[config_type] = None

    @abstractmethod
    def run(self, elements_filepath: Path, file_data: FileData, **kwargs) -> Path:
        pass

    async def run_async(self, elements_filepath: Path, file_data: FileData, **kwargs) -> Path:
        return self.run(elements_filepath=elements_filepath, file_data=file_data, **kwargs)
