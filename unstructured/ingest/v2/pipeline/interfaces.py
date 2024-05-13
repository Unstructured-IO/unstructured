import asyncio
import multiprocessing as mp
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Optional, TypeVar

from unstructured.ingest.v2.interfaces import BaseProcess
from unstructured.ingest.v2.logging import logger
from unstructured.ingest.v2.pipeline.context import PipelineContext

process_type = TypeVar("process_type", bound=BaseProcess)
iterable_input = list[dict[str, Any]]


@dataclass
class PipelineStep(ABC):
    identifier: str
    process: process_type
    context: PipelineContext

    def process_serially(self, iterable: iterable_input) -> Any:
        logger.info("processing content serially")
        if iterable:
            return [self.run(**it) for it in iterable]
        return [self.run()]

    async def _process_async(self, iterable: iterable_input) -> Any:
        if iterable:
            if len(iterable) == 1:
                return [await self.run_async(**iterable[0])]
            return await asyncio.gather(*[self.run_async(**i) for i in iterable])
        return [await self.run_async()]

    def process_async(self, iterable: iterable_input) -> Any:
        logger.info("processing content async")
        return asyncio.run(self._process_async(iterable=iterable))

    def process_multiprocess(self, iterable: iterable_input) -> Any:
        logger.info("processing content across processes")

        if iterable:
            if len(iterable) == 1:
                return [self.run(**iterable[0])]
            with mp.Pool(
                processes=self.context.num_processes,
            ) as pool:
                return pool.map(self._wrap_mp, iterable)
        return [self.run()]

    def _wrap_mp(self, input_kwargs: dict) -> Any:
        # Allow mapping of kwargs via multiprocessing map()
        return self.run(**input_kwargs)

    def __call__(self, iterable: Optional[iterable_input] = None) -> Any:
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


def log_error() -> Callable[[Callable], Callable]:
    # When running functions inside of a multiprocessing Pool, errors can get swallowed.
    # Use this to make sure the stack trace is appropriately logged

    def error_handler(func: Callable) -> Callable:
        def wrap_with_logger(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.error(
                    f"Exception raised while processing {func.__name__}: {e}", exc_info=True
                )
                raise e

        return wrap_with_logger

    return error_handler
