import logging
import typing as t
from dataclasses import dataclass, field

from unstructured.ingest.logger import ingest_log_streaming_init, logger
from unstructured.ingest.pipeline.interfaces import (
    DocFactoryNode,
    PartitionNode,
    PipelineContext,
    ReformatNode,
    SourceNode,
    WriteNode,
)
from unstructured.ingest.pipeline.utils import get_ingest_doc_hash


@dataclass
class Pipeline:
    pipeline_config: PipelineContext
    doc_factory_node: DocFactoryNode
    source_node: SourceNode
    partition_node: t.Optional[PartitionNode] = None
    write_node: t.Optional[WriteNode] = None
    reformat_nodes: t.List[ReformatNode] = field(default_factory=list)
    verbose: bool = False

    def initialize(self):
        ingest_log_streaming_init(logging.DEBUG if self.verbose else logging.INFO)

    def run(self):
        self.initialize()
        logger.info("running pipeline")
        json_docs = self.doc_factory_node()
        for doc in json_docs:
            self.pipeline_config.ingest_docs_map[get_ingest_doc_hash(doc)] = doc
        self.source_node(iterable=json_docs)
        partitioned_jsons = self.partition_node(iterable=json_docs)
        for reformat_node in self.reformat_nodes:
            reformatted_jsons = reformat_node(iterable=partitioned_jsons)
            partitioned_jsons = reformatted_jsons

        if self.write_node:
            self.write_node(iterable=partitioned_jsons)
