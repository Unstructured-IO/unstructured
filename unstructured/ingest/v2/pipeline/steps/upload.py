import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional, TypedDict

from unstructured.ingest.v2.interfaces import FileData
from unstructured.ingest.v2.interfaces.uploader import UploadContent, Uploader
from unstructured.ingest.v2.logger import logger
from unstructured.ingest.v2.pipeline.interfaces import PipelineStep, iterable_input
from unstructured.ingest.v2.pipeline.utils import sterilize_dict

STEP_ID = "upload"


class UploadStepContent(TypedDict):
    path: str
    file_data_path: str


@dataclass
class UploadStep(PipelineStep):
    process: Uploader
    identifier: str = STEP_ID

    def __str__(self):
        return f"{self.identifier} ({self.process.__class__.__name__})"

    def __post_init__(self):
        config = (
            sterilize_dict(self.process.upload_config.to_dict(redact_sensitive=True))
            if self.process.upload_config
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

    def process_whole(self, iterable: iterable_input):
        self.run(contents=iterable)

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

    def _run(self, fn: Callable, contents: list[UploadStepContent]):
        upload_contents = [
            UploadContent(path=Path(c["path"]), file_data=FileData.from_file(c["file_data_path"]))
            for c in contents
        ]
        fn(contents=upload_contents)

    async def _run_async(self, path: str, file_data_path: str, fn: Optional[Callable] = None):
        fn = fn or self.process.run_async
        fn_kwargs = {"path": Path(path), "file_data": FileData.from_file(path=file_data_path)}
        if not asyncio.iscoroutinefunction(fn):
            fn(**fn_kwargs)
        elif semaphore := self.context.semaphore:
            async with semaphore:
                await fn(**fn_kwargs)
        else:
            await fn(**fn_kwargs)
