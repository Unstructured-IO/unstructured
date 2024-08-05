from abc import ABC
from dataclasses import dataclass
from pathlib import Path
from typing import Any, TypeVar

from unstructured.ingest.enhanced_dataclass import EnhancedDataClassJsonMixin
from unstructured.ingest.v2.interfaces.connector import BaseConnector
from unstructured.ingest.v2.interfaces.file_data import FileData
from unstructured.ingest.v2.interfaces.process import BaseProcess


@dataclass
class UploaderConfig(EnhancedDataClassJsonMixin):
    pass


UploaderConfigT = TypeVar("UploaderConfigT", bound=UploaderConfig)


@dataclass
class UploadContent:
    path: Path
    file_data: FileData


@dataclass
class Uploader(BaseProcess, BaseConnector, ABC):
    upload_config: UploaderConfigT
    connector_type: str

    def is_async(self) -> bool:
        return False

    def is_batch(self) -> bool:
        return True

    def run_batch(self, contents: list[UploadContent], **kwargs: Any) -> None:
        raise NotImplementedError()

    def run(self, path: Path, file_data: FileData, **kwargs: Any) -> None:
        raise NotImplementedError()

    async def run_async(self, path: Path, file_data: FileData, **kwargs: Any) -> None:
        return self.run_batch(contents=[UploadContent(path=path, file_data=file_data)], **kwargs)
