import hashlib
import json
import logging
import multiprocessing as mp
import os.path
import typing as t
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path

from unstructured.ingest.connector.registry import create_ingest_doc_from_json
from unstructured.ingest.connector.s3 import (
    S3SourceConnector,
    SimpleS3Config,
)
from unstructured.ingest.error import PartitionError
from unstructured.ingest.interfaces import (
    BaseSourceConnector,
    EmbeddingConfig,
    IngestDocSessionHandleMixin,
    PartitionConfig,
    ReadConfig,
)
from unstructured.ingest.logger import ingest_log_streaming_init, logger
from unstructured.staging.base import convert_to_dict, elements_from_json

ingest_log_streaming_init(logging.DEBUG)


@dataclass
class PipelineContext:
    num_processes: int = 2
    pipeline_id: uuid.UUID = uuid.uuid4()
    working_dir: t.Optional[str] = None
    ingest_docs_map: dict = field(default_factory=dict)

    def get_working_dir(self) -> Path:
        if self.working_dir:
            return (Path(self.working_dir) / str(self.pipeline_id)).resolve()
        else:
            cache_path = (
                Path.home()
                / ".cache"
                / "unstructured"
                / "ingest"
                / "pipeline"
                / str(self.pipeline_id)
            )
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


class PipelineException(BaseException):
    pass


@dataclass
class Pipeline:
    pipeline_config: PipelineContext
    doc_factory_node: DocFactoryNode
    source_node: SourceNode
    partition_node: t.Optional[PartitionNode] = None
    write_node: t.Optional[WriteNode] = None
    reformat_nodes: t.List[ReformatNode] = field(default_factory=list)

    def run(self):
        logger.info(f"running pipeline {self.pipeline_config.pipeline_id}")
        json_docs = self.doc_factory_node()
        for doc in json_docs:
            json_as_dict = json.loads(doc)
            hashed = hashlib.sha256(json_as_dict.get("filename").encode()).hexdigest()[:32]
            self.pipeline_config.ingest_docs_map[hashed] = doc
        # self.source_node(iterable=json_docs)
        # partitioned_jsons = self.partition_node(iterable=json_docs)
        # for reformat_node in self.reformat_nodes:
        #     reformatted_jsons = reformat_node(iterable=partitioned_jsons)
        #     partitioned_jsons = reformatted_jsons


@dataclass
class DocFactory(DocFactoryNode):
    def initialize(self):
        self.source_doc_connector.initialize()

    def run(self) -> t.Iterable[str]:
        docs = self.source_doc_connector.get_ingest_docs()
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
        doc_filename = os.path.basename(doc.filename)
        json_path = (Path(self.get_path()) / doc_filename).resolve()
        if not self.partition_config.reprocess and json_path.is_file() and json_path.stat().st_size:
            logger.debug(f"File exists: {json_path}, skipping partition")
            return str(json_path)
        elements = doc.partition_file(
            partition_config=self.partition_config,
            strategy=self.partition_config.strategy,
            ocr_languages=self.partition_config.ocr_languages,
            encoding=self.partition_config.encoding,
            pdf_infer_table_structure=self.partition_config.pdf_infer_table_structure,
        )
        elements_dict = convert_to_dict(elements)
        with open(json_path, "w", encoding="utf8") as output_f:
            json.dump(elements_dict, output_f, ensure_ascii=False, indent=2)
        return str(json_path)


@dataclass
class Embedder(ReformatNode):
    embedder_config: EmbeddingConfig
    reprocess: bool = False

    def run(self, elements_json: str) -> str:
        elements_json_filename = os.path.basename(elements_json)
        json_path = (Path(self.get_path()) / elements_json_filename).resolve()
        if not self.reprocess and json_path.is_file() and json_path.stat().st_size:
            logger.debug(f"File exists: {json_path}, skipping embedding")
            return str(json_path)
        elements = elements_from_json(filename=elements_json)
        embedder = self.embedder_config.get_embedder()
        embedded_elements = embedder.embed_documents(elements=elements)
        elements_dict = convert_to_dict(embedded_elements)
        with open(json_path, "w", encoding="utf8") as output_f:
            json.dump(elements_dict, output_f, ensure_ascii=False, indent=2)
        return str(json_path)

    def get_path(self) -> t.Optional[Path]:
        return (Path(self.pipeline_config.get_working_dir()) / "embedded").resolve()


pipeline_config = PipelineContext(num_processes=1)
read_config = ReadConfig(preserve_downloads=True, download_dir="pipeline-test-output")
partition_config = PartitionConfig()
page_title = "Open Source Software"
auto_suggest = False


source_doc_connector = S3SourceConnector(  # type: ignore
    connector_config=SimpleS3Config(
        path="s3://utic-dev-tech-fixtures/small-pdf-set/",
        recursive=True,
        access_kwargs={"anon": True},
    ),
    read_config=read_config,
)
doc_factory = DocFactory(pipeline_config=pipeline_config, source_doc_connector=source_doc_connector)
reader = Reader(pipeline_config=pipeline_config)
partitioner = Partitioner(pipeline_config=pipeline_config, partition_config=partition_config)
embedder = Embedder(
    pipeline_config=pipeline_config,
    embedder_config=EmbeddingConfig(api_key="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"),
)

if __name__ == "__main__":
    pipeline = Pipeline(
        pipeline_config=pipeline_config,
        doc_factory_node=doc_factory,
        source_node=reader,
        partition_node=partitioner,
        reformat_nodes=[embedder],
    )
    pipeline.run()
