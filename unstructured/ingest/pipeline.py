import json
import multiprocessing as mp
import os.path
import typing as t
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path

from unstructured.ingest.connector.registry import create_ingest_doc_from_json
from unstructured.ingest.connector.wikipedia import (
    SimpleWikipediaConfig,
    WikipediaSourceConnector,
)
from unstructured.ingest.error import PartitionError
from unstructured.ingest.interfaces import (
    BaseSourceConnector,
    IngestDocSessionHandleMixin,
    PartitionConfig,
    ReadConfig,
)
from unstructured.ingest.logger import logger
from unstructured.staging.base import convert_to_dict


@dataclass
class PipelineConfig:
    output_dir: str = "structured-output"
    num_processes: int = 2
    pipeline_id: uuid.UUID = uuid.uuid4()


@dataclass
class PipelineNode(ABC):
    pipeline_config: PipelineConfig

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
        return (Path(self.pipeline_config.output_dir) / "partitioned").resolve()


class ReformatNode(PipelineNode):
    """
    Encapsulated any logic to reformat the output List[Element]
    content from partition before writing it
    """

    pass


class WriteNode(PipelineNode):
    pass


class PipelineException(BaseException):
    pass


@dataclass
class Pipeline:
    pipeline_config: PipelineConfig
    doc_factory_node: DocFactoryNode
    source_node: SourceNode
    partition_node: t.Optional[PartitionNode] = None
    write_node: t.Optional[WriteNode] = None
    reformat_nodes: t.List[ReformatNode] = field(default_factory=list)

    def run(self):
        logger.info(f"running pipeline {self.pipeline_config.pipeline_id}")
        json_docs = self.doc_factory_node()
        _ = self.source_node(iterable=json_docs)
        _ = self.partition_node(iterable=json_docs)


@dataclass
class DocFactory(DocFactoryNode):
    def initialize(self):
        self.source_doc_connector.initialize()

    def _filter_docs_with_outputs(self, docs):
        num_docs_all = len(docs)
        docs = [doc for doc in docs if not doc.has_output()]
        if self.source_doc_connector.read_config.max_docs is not None:
            if num_docs_all > self.source_doc_connector.read_config.max_docs:
                num_docs_all = self.source_doc_connector.read_config.max_docs
            docs = docs[: self.source_doc_connector.read_config.max_docs]
        num_docs_to_process = len(docs)
        if num_docs_to_process == 0:
            logger.info(
                "All docs have structured outputs, nothing to do. Use --reprocess to process all.",
            )
            return None
        elif num_docs_to_process != num_docs_all:
            logger.info(
                f"Skipping processing for {num_docs_all - num_docs_to_process} docs out of "
                f"{num_docs_all} since their structured outputs already exist, use --reprocess to "
                "reprocess those in addition to the unprocessed ones.",
            )
        return docs

    def run(self) -> t.Iterable[str]:
        docs = self.source_doc_connector.get_ingest_docs()
        if not self.source_doc_connector.read_config.reprocess:
            docs = self._filter_docs_with_outputs(docs)
            if not docs:
                return []
        json_docs = [doc.to_json() for doc in docs]
        return json_docs


@dataclass
class Reader(SourceNode):
    def run(self, ingest_doc_json: str) -> str:
        global session_handle
        doc = create_ingest_doc_from_json(ingest_doc_json)
        if isinstance(doc, IngestDocSessionHandleMixin):
            if session_handle is None:
                # create via doc.session_handle, which is a property that creates a
                # session handle if one is not already defined
                session_handle = doc.session_handle
            else:
                doc.session_handle = session_handle
        # does the work necessary to load file into filesystem
        # in the future, get_file_handle() could also be supported
        doc.get_file()
        return doc.filename


@dataclass
class Partitioner(PartitionNode):
    @PartitionError.wrap
    def run(self, ingest_doc_json) -> str:
        doc = create_ingest_doc_from_json(ingest_doc_json)
        elements = doc.partition_file(
            partition_config=self.partition_config,
            strategy=self.partition_config.strategy,
            ocr_languages=self.partition_config.ocr_languages,
            encoding=self.partition_config.encoding,
            pdf_infer_table_structure=self.partition_config.pdf_infer_table_structure,
        )
        elements_dict = convert_to_dict(elements)
        doc_filename = os.path.basename(doc.filename)
        json_path = (Path(self.get_path()) / doc_filename).resolve()
        with open(json_path, "w", encoding="utf8") as output_f:
            json.dump(elements_dict, output_f, ensure_ascii=False, indent=2)
        return json_path


pipeline_config = PipelineConfig(output_dir="pipeline-test-output", num_processes=1)
read_config = ReadConfig(preserve_downloads=True, download_dir="pipeline-test-output")
partition_config = PartitionConfig()
page_title = "Open Source Software"
auto_suggest = False


source_doc_connector = WikipediaSourceConnector(  # type: ignore
    connector_config=SimpleWikipediaConfig(
        title=page_title,
        auto_suggest=auto_suggest,
    ),
    read_config=read_config,
)
doc_factory = DocFactory(pipeline_config=pipeline_config, source_doc_connector=source_doc_connector)
reader = Reader(pipeline_config=pipeline_config)
partitioner = Partitioner(pipeline_config=pipeline_config, partition_config=partition_config)

if __name__ == "__main__":
    pipeline = Pipeline(
        pipeline_config=pipeline_config,
        doc_factory_node=doc_factory,
        source_node=reader,
        partition_node=partitioner,
    )
    pipeline.run()
