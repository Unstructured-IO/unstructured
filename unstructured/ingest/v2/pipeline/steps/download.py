import asyncio
import hashlib
import json
from dataclasses import dataclass
from typing import Callable, Optional, TypedDict, TypeVar

from unstructured.ingest.v2.interfaces import FileData, download_responses
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
        if not download_path or not download_path.exists():
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

    async def _run_async(self, fn: Callable, file_data_path: str) -> list[DownloadStepResponse]:
        file_data = FileData.from_file(path=file_data_path)
        download_path = self.process.get_download_path(file_data=file_data)
        if not self.should_download(file_data=file_data, file_data_path=file_data_path):
            logger.debug(f"Skipping download, file already exists locally: {download_path}")
            return [DownloadStepResponse(file_data_path=file_data_path, path=str(download_path))]
        fn_kwargs = {"file_data": file_data}
        if not asyncio.iscoroutinefunction(fn):
            download_results = fn(**fn_kwargs)
        elif semaphore := self.context.semaphore:
            async with semaphore:
                download_results = await fn(**fn_kwargs)
        else:
            download_results = await fn(**fn_kwargs)
        return self.create_step_results(
            current_file_data_path=file_data_path, download_results=download_results
        )

    def create_step_results(
        self, current_file_data_path: str, download_results: download_responses
    ) -> list[DownloadStepResponse]:
        if not isinstance(download_results, list):
            return [
                DownloadStepResponse(
                    file_data_path=current_file_data_path, path=str(download_results["path"])
                )
            ]
            # Supplemental results generated as part of the download process
        download_step_results = []
        for res in download_results:
            file_data_path = self.persist_new_file_data(file_data=res["file_data"])
            download_step_results.append(
                DownloadStepResponse(file_data_path=file_data_path, path=res["path"])
            )
        return download_step_results

    def persist_new_file_data(self, file_data: FileData) -> str:
        record_hash = self.get_hash(extras=[file_data.identifier])
        filename = f"{record_hash}.json"
        filepath = (self.cache_dir / filename).resolve()
        filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(str(filepath), "w") as f:
            json.dump(file_data.to_dict(), f, indent=2)
        return str(filepath)

    def get_hash(self, extras: Optional[list[str]]) -> str:
        hashable_string = json.dumps(
            sterilize_dict(self.process.download_config.to_dict()), sort_keys=True
        )
        if extras:
            hashable_string += "".join(extras)
        return hashlib.sha256(hashable_string.encode()).hexdigest()[:12]
