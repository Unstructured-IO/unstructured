from dataclasses import dataclass
from pathlib import Path
from typing import TypedDict

from unstructured.ingest.v2.interfaces.upload_stager import UploadStager
from unstructured.ingest.v2.pipeline.interfaces import PipelineStep, log_error

STEP_ID = "upload_stage"


class UploadStageStepResponse(TypedDict):
    file_data_path: str
    path: str


@dataclass(kw_only=True)
class UploadStageStep(PipelineStep):
    identifier: str = STEP_ID
    process: UploadStager

    @log_error()
    def run(self, path: str, file_data_path: str) -> UploadStageStepResponse:
        path = Path(path)
        staged_output_path = self.process.run(elements_filepath=path)
        return UploadStageStepResponse(file_data_path=file_data_path, path=str(staged_output_path))

    async def run_async(self, path: str, file_data_path: str) -> UploadStageStepResponse:
        path = Path(path)
        staged_output_path = await self.process.run_async(elements_filepath=path)
        return UploadStageStepResponse(file_data_path=file_data_path, path=str(staged_output_path))
