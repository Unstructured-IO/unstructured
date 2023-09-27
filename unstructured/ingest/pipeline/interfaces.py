import multiprocessing as mp
import typing as t
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path

from unstructured.ingest.interfaces import (
    BaseSourceConnector,
    PartitionConfig,
)
from unstructured.ingest.logger import logger


@dataclass
class PipelineContext:
    num_processes: int = 2
    working_dir: t.Optional[str] = None
    ingest_docs_map: dict = field(default_factory=dict)

    def get_working_dir(self) -> Path:
        if self.working_dir:
            return (Path(self.working_dir)).resolve()
        else:
            cache_path = Path.home() / ".cache" / "unstructured" / "ingest" / "pipeline"
            if not cache_path.exists():
                cache_path.mkdir(parents=True, exist_ok=True)
            return cache_path.resolve()


@dataclass
class PipelineNode(ABC):
    pipeline_config: PipelineContext

    def __call__(self, iterable: t.Iterable[t.Any] = None):
        iterable = iterable if iterable else []
        self.initialize()
        if self.pipeline_config.num_processes == 1 or not self.supported_multiprocessing():
            if iterable:
                self.result = [self.run(it) for it in iterable]
            else:
                self.result = self.run()
        else:
            logger.info(
                f"processing {len(iterable)} items via "
                f"{self.pipeline_config.num_processes} processes",
            )
            with mp.Pool(
                processes=self.pipeline_config.num_processes,
            ) as pool:
                self.result = pool.map(self.run, iterable)
        return self.result

    def supported_multiprocessing(self) -> bool:
        return True

    @abstractmethod
    def run(self):
        pass

    def initialize(self):
        if path := self.get_path():
            logger.info(f"Creating {path}")
            path.mkdir(parents=True, exist_ok=True)

    def get_path(self) -> t.Optional[Path]:
        return None


@dataclass
class DocFactoryNode(PipelineNode):
    source_doc_connector: BaseSourceConnector

    @abstractmethod
    def run(self) -> t.Iterable[str]:
        pass

    def supported_multiprocessing(self) -> bool:
        return False


class SourceNode(PipelineNode):
    """
    Encapsulated logic to pull from a data source via base ingest docs
    Output of logic expected to be the json outputs of the data itself
    """

    @abstractmethod
    def run(self, ingest_doc_json: str) -> str:
        pass


@dataclass
class PartitionNode(PipelineNode):
    """
    Encapsulates logic to run partition on the json files as the output of the source node
    """

    partition_config: PartitionConfig
    partition_kwargs: dict = field(default_factory=dict)

    @abstractmethod
    def run(self, json_path: str) -> str:
        pass

    def get_path(self) -> t.Optional[Path]:
        return (Path(self.pipeline_config.get_working_dir()) / "partitioned").resolve()


class ReformatNode(PipelineNode):
    """
    Encapsulated any logic to reformat the output List[Element]
    content from partition before writing it
    """

    pass


class WriteNode(PipelineNode):
    pass
