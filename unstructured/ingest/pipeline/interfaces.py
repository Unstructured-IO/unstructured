import hashlib
import json
import logging
import multiprocessing as mp
import typing as t
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from multiprocessing.managers import DictProxy
from pathlib import Path

import backoff
from dataclasses_json import DataClassJsonMixin

from unstructured.ingest.error import SourceConnectionNetworkError
from unstructured.ingest.ingest_backoff import RetryHandler
from unstructured.ingest.interfaces import (
    BaseDestinationConnector,
    BaseSourceConnector,
    PartitionConfig,
    ProcessorConfig,
    ReadConfig,
    RetryStrategyConfig,
)
from unstructured.ingest.logger import ingest_log_streaming_init, logger


@dataclass
class PipelineContext(ProcessorConfig):
    """
    Data that gets shared across each pipeline node
    """

    def __post_init__(self):
        self._ingest_docs_map: t.Optional[DictProxy] = None

    @property
    def ingest_docs_map(self) -> DictProxy:
        if self._ingest_docs_map is None:
            raise ValueError("ingest_docs_map never initialized")
        return self._ingest_docs_map

    @ingest_docs_map.setter
    def ingest_docs_map(self, value: DictProxy):
        self._ingest_docs_map = value


@dataclass
class PipelineNode(DataClassJsonMixin, ABC):
    """
    Class that encapsulates logic to run during a single pipeline step
    """

    pipeline_context: PipelineContext

    def __call__(self, iterable: t.Optional[t.Iterable[t.Any]] = None) -> t.Any:
        iterable = iterable if iterable else []
        if iterable:
            logger.info(
                f"Calling {self.__class__.__name__} " f"with {len(iterable)} docs",  # type: ignore
            )

        self.initialize()
        if not self.supported_multiprocessing():
            if iterable:
                self.result = self.run(iterable)
            else:
                self.result = self.run()
        elif self.pipeline_context.num_processes == 1:
            if iterable:
                self.result = [self.run(it) for it in iterable]
            else:
                self.result = self.run()
        else:
            with mp.Pool(
                processes=self.pipeline_context.num_processes,
                initializer=ingest_log_streaming_init,
                initargs=(logging.DEBUG if self.pipeline_context.verbose else logging.INFO,),
            ) as pool:
                self.result = pool.map(self.run, iterable)
        # Remove None which may be caused by failed docs that didn't raise an error
        if isinstance(self.result, t.Iterable):
            self.result = [r for r in self.result if r is not None]
        return self.result

    def supported_multiprocessing(self) -> bool:
        return True

    @abstractmethod
    def run(self, *args, **kwargs) -> t.Optional[t.Any]:
        pass

    def initialize(self):
        if path := self.get_path():
            logger.info(f"Creating {path}")
            path.mkdir(parents=True, exist_ok=True)
        ingest_log_streaming_init(logging.DEBUG if self.pipeline_context.verbose else logging.INFO)

    def get_path(self) -> t.Optional[Path]:
        return None


@dataclass
class DocFactoryNode(PipelineNode):
    """
    Encapsulated logic to generate a list of ingest docs
    """

    source_doc_connector: BaseSourceConnector

    def initialize(self):
        logger.info(
            f"Running doc factory to generate ingest docs. "
            f"Source connector: {self.source_doc_connector.to_json()}",
        )
        super().initialize()
        self.source_doc_connector.initialize()

    @abstractmethod
    def run(self, *args, **kwargs) -> t.Iterable[dict]:
        pass

    def supported_multiprocessing(self) -> bool:
        return False


@dataclass
class SourceNode(PipelineNode):
    """A pipeline node representing logic to pull data from a source using base ingest documents.

    This class encapsulates the logic for pulling data from a specified source using base ingest
    documents. The output of this logic is expected to be in JSON format representing the data
    itself.

    Attributes:
        read_config: A configuration object specifying how to read data from the source.
        retry_strategy_config: Optional configuration specifying the strategy for network errors.

    Properties:
        retry_strategy: A retry handler configured based on the retry strategy configuration.

    Methods:
        initialize: Initializes the source node and logs the process.
        run: Abstract method for downloading data associated with ingest documents.
    """

    read_config: ReadConfig
    retry_strategy_config: t.Optional[RetryStrategyConfig] = None

    @property
    def retry_strategy(self) -> t.Optional[RetryHandler]:
        if retry_strategy_config := self.retry_strategy_config:
            return RetryHandler(
                backoff.expo,
                SourceConnectionNetworkError,
                max_time=retry_strategy_config.max_retry_time,
                max_tries=retry_strategy_config.max_retries,
                logger=logger,
                start_log_level=logger.level,
                backoff_log_level=logger.level,
            )
        return None

    def initialize(self):
        logger.info("Running source node to download data associated with ingest docs")
        super().initialize()

    @abstractmethod
    def run(self, ingest_doc_json: str) -> t.Optional[str]:
        pass


@dataclass
class PartitionNode(PipelineNode):
    """
    Encapsulates logic to run partition on the json files as the output of the source node
    """

    partition_config: PartitionConfig
    partition_kwargs: dict = field(default_factory=dict)

    def initialize(self):
        logger.info(
            f"Running partition node to extract content from json files. "
            f"Config: {self.partition_config.to_json()}, "
            f"partition kwargs: {json.dumps(self.partition_kwargs)}]",
        )
        super().initialize()

    def create_hash(self) -> str:
        hash_dict = self.partition_config.to_dict()
        hash_dict["partition_kwargs"] = self.partition_kwargs
        return hashlib.sha256(json.dumps(hash_dict, sort_keys=True).encode()).hexdigest()[:32]

    @abstractmethod
    def run(self, json_path: str) -> t.Optional[str]:
        pass

    def get_path(self) -> Path:
        return (Path(self.pipeline_context.work_dir) / "partitioned").resolve()


@dataclass
class ReformatNode(PipelineNode, ABC):
    """
    Encapsulated any logic to reformat the output List[Element]
    content from partition before writing it
    """

    @abstractmethod
    def run(self, elements_json: str) -> t.Optional[str]:
        pass


@dataclass
class WriteNode(PipelineNode):
    """
    Encapsulated logic to write the final result to a downstream data connection
    """

    dest_doc_connector: BaseDestinationConnector

    @abstractmethod
    def run(self, json_paths: t.List[str]):
        pass

    def initialize(self):
        logger.info(
            f"Running write node to upload content. "
            f"Destination connector: {self.dest_doc_connector.to_json(redact_sensitive=True)}]",
        )
        super().initialize()
        self.dest_doc_connector.initialize()

    def supported_multiprocessing(self) -> bool:
        return False


@dataclass
class CopyNode(PipelineNode):
    """
    Encapsulated logic to copy the final result of the pipeline to the designated output location.
    """

    def initialize(self):
        logger.info("Running copy node to move content to desired output location")
        super().initialize()

    @abstractmethod
    def run(self, json_path: str):
        pass


@dataclass
class PermissionsNode(PipelineNode):
    """
    Encapsulated logic to do operations on permissions related data.
    """

    def initialize(self):
        logger.info("Running permissions node to cleanup the permissions folder")
        super().initialize()

    @abstractmethod
    def run(self):
        pass
