import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, TypeVar

from unstructured.ingest.v2.interfaces import FileData
from unstructured.ingest.v2.interfaces.downloader import Downloader
from unstructured.ingest.v2.pipeline.interfaces import PipelineStep

download_type = TypeVar("download_type", bound=Downloader)

STEP_ID = "download"


@dataclass
class DownloadStepResponse:
    record_id: str
    path: Path


@dataclass(kw_only=True)
class DownloadStep(PipelineStep):
    identifier: str = STEP_ID
    process: download_type

    @staticmethod
    def is_float(value: str):
        try:
            float(value)
            return True
        except ValueError:
            return False

    def should_download(self, file_data: FileData) -> bool:
        if self.context.re_download:
            return True
        download_path = self.process.get_download_path(file_data=file_data)
        if not download_path.exists():
            return True
        if (
            download_path.is_file()
            and file_data.metadata.date_modified
            and self.is_float(file_data.metadata.date_modified)
            and download_path.stat().st_mtime > float(file_data.metadata.date_modified)
        ):
            return True
        return False

    def get_file_data(self, path: str) -> FileData:
        with open(path, "rb") as f:
            file_data_dict = json.load(f)
        file_data = FileData.from_dict(file_data_dict)
        return file_data

    def run(self, file_data_path: str) -> str:
        file_data = self.get_file_data(path=file_data_path)
        download_path = self.process.get_download_path(file_data=file_data)
        if not self.should_download(file_data=file_data):
            return str(download_path)

        download_path = self.process.run(file_data=file_data)
        return str(download_path)

    async def run_async(self, file_data_path: str) -> Path:
        file_data = self.get_file_data(path=file_data_path)
        download_path = self.process.get_download_path(file_data=file_data)
        if not self.should_download(file_data=file_data):
            return download_path

        download_path = await self.process.run_async(file_data=file_data)
        return download_path

    def get_hash(self, extras: Optional[list[str]]) -> str:
        hashable_string = json.dumps(self.process.download_config.to_dict())
        if extras:
            hashable_string += "".join(extras)
        return hashlib.sha256(hashable_string.encode()).hexdigest()[:12]
