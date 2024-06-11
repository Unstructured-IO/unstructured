from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any, TypeVar

from unstructured.ingest.enhanced_dataclass import EnhancedDataClassJsonMixin
from unstructured.ingest.v2.interfaces.file_data import FileData
from unstructured.ingest.v2.interfaces.process import BaseProcess


@dataclass
class UploadStagerConfig(EnhancedDataClassJsonMixin):
    pass


UploadStagerConfigT = TypeVar("UploadStagerConfigT", bound=UploadStagerConfig)


@dataclass
class UploadStager(BaseProcess, ABC):
    upload_stager_config: UploadStagerConfigT

    @abstractmethod
    def run(
        self,
        elements_filepath: Path,
        file_data: FileData,
        output_dir: Path,
        output_filename: str,
        **kwargs: Any
    ) -> Path:
        pass

    async def run_async(
        self,
        elements_filepath: Path,
        file_data: FileData,
        output_dir: Path,
        output_filename: str,
        **kwargs: Any
    ) -> Path:
        return self.run(
            elements_filepath=elements_filepath,
            output_dir=output_dir,
            output_filename=output_filename,
            file_data=file_data,
            **kwargs
        )
