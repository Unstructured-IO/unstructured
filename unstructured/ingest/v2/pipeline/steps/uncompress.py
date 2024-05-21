from pathlib import Path
from typing import TypedDict

from unstructured.ingest.v2.interfaces.file_data import FileData
from unstructured.ingest.v2.logger import logger
from unstructured.ingest.v2.pipeline.interfaces import PipelineStep
from unstructured.ingest.v2.pipeline.utils import sterilize_dict
from unstructured.ingest.v2.processes.uncompress import Uncompressor

STEP_ID = "uncompress"


class UncompressStepResponse(TypedDict):
    file_data_path: str
    path: str


class UncompressStep(PipelineStep):
    process: Uncompressor
    identifier: str = STEP_ID

    def __post_init__(self):
        config = (
            sterilize_dict(self.process.config.to_dict(redact_sensitive=True))
            if self.process.config
            else None
        )
        logger.info(f"Created {self.identifier} with configs: {config}")

    def _run(self, path: str, file_data_path: str) -> list[UncompressStepResponse]:
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

    async def _run_async(self, path: str, file_data_path: str) -> list[UncompressStepResponse]:
        file_data = FileData.from_file(path=file_data_path)
        if semaphore := self.context.semaphore:
            async with semaphore:
                new_file_data = await self.process.run_async(file_data=file_data)
        else:
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
