import hashlib
import json
from dataclasses import dataclass
from typing import Optional, TypedDict, TypeVar

from unstructured.ingest.v2.interfaces import FileData
from unstructured.ingest.v2.interfaces.downloader import Downloader
from unstructured.ingest.v2.logger import logger
from unstructured.ingest.v2.pipeline.interfaces import PipelineStep
from unstructured.ingest.v2.pipeline.utils import sterilize_dict

DownloaderT = TypeVar("DownloaderT", bound=Downloader)

STEP_ID = "download"


class DownloadStepResponse(TypedDict):
    file_data_path: str
    path: str


@dataclass
class DownloadStep(PipelineStep):
    process: DownloaderT
    identifier: str = STEP_ID

    def __str__(self):
        return f"{self.identifier} ({self.process.__class__.__name__})"

    def __post_init__(self):
        config = (
            sterilize_dict(self.process.download_config.to_dict(redact_sensitive=True))
            if self.process.download_config
            else None
        )
        connection_config = (
            sterilize_dict(self.process.connection_config.to_dict(redact_sensitive=True))
            if self.process.connection_config
            else None
        )
        logger.info(
            f"Created {self.identifier} with configs: {config}, "
            f"connection configs: {connection_config}"
        )

    @staticmethod
    def is_float(value: str):
        try:
            float(value)
            return True
        except ValueError:
            return False

    def should_download(self, file_data: FileData, file_data_path: str) -> bool:
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
            # Also update file data to mark this to reprocess since this won't change the filename
            file_data.reprocess = True
            file_data.to_file(path=file_data_path)
            return True
        return False

    def _run(self, file_data_path: str) -> list[DownloadStepResponse]:
        file_data = FileData.from_file(path=file_data_path)
        download_path = self.process.get_download_path(file_data=file_data)
        if not self.should_download(file_data=file_data, file_data_path=file_data_path):
            logger.debug(f"Skipping download, file already exists locally: {download_path}")
            return [DownloadStepResponse(file_data_path=file_data_path, path=str(download_path))]

        download_path = self.process.run(file_data=file_data)
        return [DownloadStepResponse(file_data_path=file_data_path, path=str(download_path))]

    async def _run_async(self, file_data_path: str) -> list[DownloadStepResponse]:
        file_data = FileData.from_file(path=file_data_path)
        download_path = self.process.get_download_path(file_data=file_data)
        if not self.should_download(file_data=file_data, file_data_path=file_data_path):
            logger.debug(f"Skipping download, file already exists locally: {download_path}")
            return [DownloadStepResponse(file_data_path=file_data_path, path=str(download_path))]
        if semaphore := self.context.semaphore:
            async with semaphore:
                download_path = await self.process.run_async(file_data=file_data)
        else:
            download_path = await self.process.run_async(file_data=file_data)
        return [DownloadStepResponse(file_data_path=file_data_path, path=str(download_path))]

    def get_hash(self, extras: Optional[list[str]]) -> str:
        hashable_string = json.dumps(self.process.download_config.to_dict(), sort_keys=True)
        if extras:
            hashable_string += "".join(extras)
        return hashlib.sha256(hashable_string.encode()).hexdigest()[:12]
