import asyncio
import multiprocessing as mp
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Optional, TypeVar

from unstructured.ingest.v2.interfaces import BaseProcess
from unstructured.ingest.v2.logging import logger
from unstructured.ingest.v2.pipeline.context import PipelineContext

process_type = TypeVar("process_type", bound=BaseProcess)


@dataclass
class PipelineStep(ABC):
    identifier: str
    process: process_type
    context: PipelineContext

    def process_serially(self, iterable: Iterable[Any]) -> Any:
        if iterable:
            return [self.run(it) for it in iterable]
        return self.run()

    async def _process_async(self, iterable: Iterable[Any]) -> Any:
        if iterable:
            return await asyncio.gather(*[self.run_async(i) for i in iterable])
        return await self.run_async()

    def process_async(self, iterable: Iterable[Any]) -> Any:
        return asyncio.run(self._process_async(iterable=iterable))

    def process_multiprocess(self, iterable: Iterable[Any]) -> Any:
        if iterable:
            with mp.Pool(
                processes=self.context.num_processes,
            ) as pool:
                return pool.map(self.run, iterable)
        return self.run()

    def __call__(self, iterable: Optional[Iterable[Any]] = None) -> Any:
        iterable = iterable or []
        if iterable:
            logger.info(
                f"Calling {self.__class__.__name__} " f"with {len(iterable)} docs",  # type: ignore
            )
        if self.context.disable_parallelism:
            return self.process_serially(iterable=iterable)
        if self.process.is_async():
            return self.process_async(iterable=iterable)
        return self.process_multiprocess(iterable=iterable)

    def run(self, *args, **kwargs) -> Optional[Any]:
        raise NotImplementedError

    async def run_async(self, *args, **kwargs) -> Optional[Any]:
        raise NotImplementedError

    @abstractmethod
    def get_hash(self, extras: Optional[list[str]]) -> str:
        pass

    @property
    def cache_dir(self) -> Path:
        return Path(self.context.work_dir) / self.identifier
