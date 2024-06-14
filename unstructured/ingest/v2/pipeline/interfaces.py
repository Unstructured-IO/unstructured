import asyncio
import logging
import multiprocessing as mp
from abc import ABC
from dataclasses import dataclass
from functools import wraps
from pathlib import Path
from time import time
from typing import Any, Callable, Optional, TypeVar

from tqdm import tqdm
from tqdm.asyncio import tqdm as tqdm_asyncio

from unstructured.ingest.v2.interfaces import BaseProcess, ProcessorConfig
from unstructured.ingest.v2.logger import logger, make_default_logger

BaseProcessT = TypeVar("BaseProcessT", bound=BaseProcess)
iterable_input = list[dict[str, Any]]


def timed(func):
    @wraps(func)
    def time_it(self, *args, **kwargs):
        start = time()
        try:
            return func(self, *args, **kwargs)
        finally:
            if func.__name__ == "__call__":
                reported_name = f"{self.__class__.__name__} [cls]"
            else:
                reported_name = func.__name__
            logger.info(f"{reported_name} took {time() - start} seconds")

    return time_it


@dataclass
class PipelineStep(ABC):
    process: BaseProcessT
    context: ProcessorConfig
    identifier: str

    def __str__(self):
        return self.identifier

    def process_serially(self, iterable: iterable_input) -> Any:
        logger.info("processing content serially")
        if iterable:
            if len(iterable) == 1:
                return [self.run(**iterable[0])]
            if self.context.tqdm:
                return [self.run(**it) for it in tqdm(iterable, desc=self.identifier)]
            return [self.run(**it) for it in iterable]
        return [self.run()]

    async def _process_async(self, iterable: iterable_input) -> Any:
        if iterable:
            if len(iterable) == 1:
                return [await self.run_async(**iterable[0])]
            if self.context.tqdm:
                return await tqdm_asyncio.gather(
                    *[self.run_async(**i) for i in iterable], desc=self.identifier
                )
            return await asyncio.gather(*[self.run_async(**i) for i in iterable])
        return [await self.run_async()]

    def process_async(self, iterable: iterable_input) -> Any:
        logger.info("processing content async")
        return asyncio.run(self._process_async(iterable=iterable))

    def process_multiprocess(self, iterable: iterable_input) -> Any:
        logger.info("processing content across processes")

        if iterable:
            if len(iterable) == 1:
                return [self.process_serially(iterable)]
            if self.context.num_processes == 1:
                return self.process_serially(iterable)
            with mp.Pool(
                processes=self.context.num_processes,
                initializer=self._set_log_level,
                initargs=(logging.DEBUG if self.context.verbose else logging.INFO,),
            ) as pool:
                if self.context.tqdm:
                    return list(
                        tqdm(
                            pool.imap_unordered(func=self._wrap_mp, iterable=iterable),
                            total=len(iterable),
                            desc=self.identifier,
                        )
                    )
                return pool.map(self._wrap_mp, iterable)
        return [self.run()]

    def _wrap_mp(self, input_kwargs: dict) -> Any:
        # Allow mapping of kwargs via multiprocessing map()
        return self.run(**input_kwargs)

    def _set_log_level(self, log_level: int):
        # Set the log level for each spawned process when using multiprocessing pool
        make_default_logger(log_level)

    @timed
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

    def _run(self, fn: Callable, **kwargs: Any) -> Optional[Any]:
        return asyncio.run(self.run_async(_fn=fn, **kwargs))

    async def _run_async(self, fn: Callable, **kwargs: Any) -> Optional[Any]:
        raise NotImplementedError

    def run(self, _fn: Optional[Callable] = None, **kwargs: Any) -> Optional[Any]:
        try:
            fn = _fn or self.process.run
            return self._run(fn=fn, **kwargs)
        except Exception as e:
            logger.error(f"Exception raised while running {self.identifier}", exc_info=e)
            if "file_data_path" in kwargs:
                self.context.status[kwargs["file_data_path"]] = {self.identifier: str(e)}
            if self.context.raise_on_error:
                raise e
            return None

    async def run_async(self, _fn: Optional[Callable] = None, **kwargs: Any) -> Optional[Any]:
        try:
            fn = _fn or self.process.run_async
            return await self._run_async(fn=fn, **kwargs)
        except Exception as e:
            logger.error(f"Exception raised while running {self.identifier}", exc_info=e)
            if "file_data_path" in kwargs:
                self.context.status[kwargs["file_data_path"]] = {self.identifier: str(e)}
            if self.context.raise_on_error:
                raise e
            return None

    @property
    def cache_dir(self) -> Path:
        return Path(self.context.work_dir) / self.identifier
