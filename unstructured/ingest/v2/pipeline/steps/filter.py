import asyncio
from dataclasses import dataclass
from typing import Callable, Optional

from unstructured.ingest.v2.interfaces.file_data import FileData
from unstructured.ingest.v2.logger import logger
from unstructured.ingest.v2.pipeline.interfaces import PipelineStep
from unstructured.ingest.v2.pipeline.utils import sterilize_dict
from unstructured.ingest.v2.processes.filter import Filterer

STEP_ID = "filter"


@dataclass
class FilterStep(PipelineStep):
    process: Filterer
    identifier: str = STEP_ID

    def __post_init__(self):
        config = (
            sterilize_dict(self.process.config.to_dict(redact_sensitive=True))
            if self.process.config
            else None
        )
        logger.info(f"Created {self.identifier} with configs: {config}")

    async def _run_async(self, fn: Callable, file_data_path: str, **kwargs) -> Optional[dict]:
        file_data = FileData.from_file(path=file_data_path)
        fn_kwargs = {"file_data": file_data}
        if not asyncio.iscoroutinefunction(fn):
            resp = fn(**fn_kwargs)
        elif semaphore := self.context.semaphore:
            async with semaphore:
                resp = await fn(**fn_kwargs)
        else:
            resp = await fn(**fn_kwargs)

        if resp:
            return {"file_data_path": file_data_path}
        return None
