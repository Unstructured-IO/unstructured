from dataclasses import dataclass
from pathlib import Path
from typing import Optional, TypedDict

from unstructured.ingest.v2.interfaces import FileData
from unstructured.ingest.v2.interfaces.uploader import UploadContent, Uploader
from unstructured.ingest.v2.pipeline.interfaces import PipelineStep, log_error

STEP_ID = "upload"


class UploadStepContent(TypedDict):
    path: str
    file_data_path: str


@dataclass(kw_only=True)
class UploadStep(PipelineStep):
    identifier: str = STEP_ID
    process: Uploader

    def get_hash(self, extras: Optional[list[str]]) -> str:
        pass

    @log_error()
    def run(self, contents: list[UploadStepContent]):
        upload_contents = [
            UploadContent(path=Path(c["path"]), file_data=FileData.from_file(c["file_data_path"]))
            for c in contents
        ]
        self.process.run(contents=upload_contents)

    async def run_async(self, contents: list[UploadStepContent]):
        upload_contents = [
            UploadContent(path=Path(c["path"]), file_data=FileData.from_file(c["file_data_path"]))
            for c in contents
        ]
        await self.process.run_async(contents=upload_contents)
