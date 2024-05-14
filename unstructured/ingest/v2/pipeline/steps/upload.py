import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, TypedDict

from unstructured.ingest.v2.interfaces import FileData
from unstructured.ingest.v2.interfaces.uploader import UploadContent, Uploader
from unstructured.ingest.v2.logging import logger
from unstructured.ingest.v2.pipeline.interfaces import PipelineStep, iterable_input, log_error

STEP_ID = "upload"


class UploadStepContent(TypedDict):
    path: str
    file_data_path: str


@dataclass(kw_only=True)
class UploadStep(PipelineStep):
    identifier: str = STEP_ID
    process: Uploader

    def process_whole(self, iterable: iterable_input):
        self.run(iterable)

    async def _process_async(self, iterable: iterable_input):
        return await asyncio.gather(*[self.run_async(**i) for i in iterable])

    def process_async(self, iterable: iterable_input):
        logger.info("processing content async")
        return asyncio.run(self._process_async(iterable=iterable))

    def __call__(self, iterable: iterable_input):
        logger.info(
            f"Calling {self.__class__.__name__} " f"with {len(iterable)} docs",  # type: ignore
        )
        if self.process.is_async():
            self.process_async(iterable=iterable)
        else:
            self.process_whole(iterable=iterable)

    def get_hash(self, extras: Optional[list[str]]) -> str:
        pass

    @log_error()
    def run(self, contents: list[UploadStepContent]):
        upload_contents = [
            UploadContent(path=Path(c["path"]), file_data=FileData.from_file(c["file_data_path"]))
            for c in contents
        ]
        self.process.run(contents=upload_contents)

    async def run_async(self, path: str, file_data_path: str):
        await self.process.run_async(
            path=Path(path), file_data=FileData.from_file(path=file_data_path)
        )
