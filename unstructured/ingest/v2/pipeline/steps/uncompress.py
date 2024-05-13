from dataclasses import dataclass
from pathlib import Path
from typing import Optional, TypedDict

from unstructured.ingest.v2.interfaces.file_data import FileData
from unstructured.ingest.v2.pipeline.interfaces import PipelineStep, log_error
from unstructured.ingest.v2.processes.uncompress import Uncompressor

STEP_ID = "uncompress"


class UncompressStepResponse(TypedDict):
    file_data_path: str
    path: str


@dataclass(kw_only=True)
class UncompressStep(PipelineStep):
    identifier: str = STEP_ID
    process: Uncompressor

    def get_hash(self, extras: Optional[list[str]]) -> str:
        pass

    @log_error()
    def run(self, path: str, file_data_path: str) -> list[UncompressStepResponse]:
        file_data = FileData.from_file(path=file_data_path)
        new_file_data = self.process.run(file_data=file_data)
        responses = []
        for new_file in new_file_data:
            new_file_data_path = Path(file_data_path).parent / f"{new_file.identifier}.json"
            new_file.to_file(path=str(new_file_data_path.resolve()))
            responses.append(
                UncompressStepResponse(
                    path=new_file.source_identifiers.fullpath,
                    file_data_path=str(new_file_data_path),
                )
            )
        return responses

    async def run_async(self, path: str, file_data_path: str) -> list[UncompressStepResponse]:
        file_data = FileData.from_file(path=file_data_path)
        new_file_data = await self.process.run_async(file_data=file_data)
        responses = []
        for new_file in new_file_data:
            new_file_data_path = Path(file_data_path).parent / f"{new_file.identifier}.json"
            new_file.to_file(path=str(new_file_data_path.resolve()))
            responses.append(
                UncompressStepResponse(
                    path=new_file.source_identifiers.fullpath,
                    file_data_path=str(new_file_data_path),
                )
            )
        return responses
