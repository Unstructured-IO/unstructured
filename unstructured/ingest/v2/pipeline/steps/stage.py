import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, TypedDict

from unstructured.ingest.v2.interfaces.file_data import FileData
from unstructured.ingest.v2.interfaces.upload_stager import UploadStager
from unstructured.ingest.v2.logger import logger
from unstructured.ingest.v2.pipeline.interfaces import PipelineStep
from unstructured.ingest.v2.pipeline.utils import sterilize_dict

STEP_ID = "upload_stage"


class UploadStageStepResponse(TypedDict):
    file_data_path: str
    path: str


@dataclass
class UploadStageStep(PipelineStep):
    process: UploadStager
    identifier: str = STEP_ID

    def __str__(self):
        return f"{self.identifier} ({self.process.__class__.__name__})"

    def __post_init__(self):
        config = (
            sterilize_dict(self.process.upload_stager_config.to_dict(redact_sensitive=True))
            if self.process.upload_stager_config
            else None
        )
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Created {self.identifier} with configs: {config}")

    def _run(self, path: str, file_data_path: str) -> UploadStageStepResponse:
        path = Path(path)
        staged_output_path = self.process.run(
            elements_filepath=path,
            file_data=FileData.from_file(path=file_data_path),
            output_dir=self.cache_dir,
            output_filename=self.get_hash(extras=[path.name]),
        )
        return UploadStageStepResponse(file_data_path=file_data_path, path=str(staged_output_path))

    async def _run_async(self, path: str, file_data_path: str) -> UploadStageStepResponse:
        path = Path(path)
        if semaphore := self.context.semaphore:
            async with semaphore:
                staged_output_path = await self.process.run_async(
                    elements_filepath=path,
                    file_data=FileData.from_file(path=file_data_path),
                    output_dir=self.cache_dir,
                    output_filename=self.get_hash(extras=[path.name]),
                )
        else:
            staged_output_path = await self.process.run_async(
                elements_filepath=path,
                file_data=FileData.from_file(path=file_data_path),
                output_dir=self.cache_dir,
                output_filename=self.get_hash(extras=[path.name]),
            )
        return UploadStageStepResponse(file_data_path=file_data_path, path=str(staged_output_path))

    def get_hash(self, extras: Optional[list[str]]) -> str:
        hashable_string = json.dumps(
            self.process.upload_stager_config.to_dict(), sort_keys=True, ensure_ascii=True
        )
        if extras:
            hashable_string += "".join(extras)
        return hashlib.sha256(hashable_string.encode()).hexdigest()[:12]
