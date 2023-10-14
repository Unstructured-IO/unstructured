import logging
import multiprocessing as mp
import typing as t
from dataclasses import dataclass, field

from dataclasses_json import DataClassJsonMixin

from unstructured.ingest.logger import ingest_log_streaming_init, logger
from unstructured.ingest.pipeline.copy import Copier
from unstructured.ingest.pipeline.interfaces import (
    DocFactoryNode,
    PartitionNode,
    PipelineContext,
    ReformatNode,
    SourceNode,
    WriteNode,
)
from unstructured.ingest.pipeline.permissions import PermissionsDataCleaner
from unstructured.ingest.pipeline.utils import get_ingest_doc_hash


@dataclass
class Pipeline(DataClassJsonMixin):
    pipeline_context: PipelineContext
    doc_factory_node: DocFactoryNode
    source_node: SourceNode
    partition_node: PartitionNode
    write_node: t.Optional[WriteNode] = None
    reformat_nodes: t.List[ReformatNode] = field(default_factory=list)
    permissions_node: t.Optional[PermissionsDataCleaner] = None

    def initialize(self):
        ingest_log_streaming_init(logging.DEBUG if self.pipeline_context.verbose else logging.INFO)

    def get_nodes_str(self):
        nodes = [self.doc_factory_node, self.source_node, self.partition_node]
        nodes.extend(self.reformat_nodes)
        if self.write_node:
            nodes.append(self.write_node)
        nodes.append(Copier(pipeline_context=self.pipeline_context))
        return " -> ".join([node.__class__.__name__ for node in nodes])

    def run(self):
        logger.info(
            f"running pipeline: {self.get_nodes_str()} "
            f"with config: {self.pipeline_context.to_json()}",
        )
        self.initialize()
        manager = mp.Manager()
        self.pipeline_context.ingest_docs_map = manager.dict()
        json_docs = self.doc_factory_node()
        if not json_docs:
            logger.info("no docs found to process")
            return
        logger.info(
            f"processing {len(json_docs)} docs via "
            f"{self.pipeline_context.num_processes} processes",
        )
        for doc in json_docs:
            self.pipeline_context.ingest_docs_map[get_ingest_doc_hash(doc)] = doc
        fetched_filenames = self.source_node(iterable=json_docs)
        if not fetched_filenames:
            logger.info("No files to run partition over")
            return
        partitioned_jsons = self.partition_node(iterable=json_docs)
        if not partitioned_jsons:
            logger.info("No files to process after partitioning")
            return
        for reformat_node in self.reformat_nodes:
            reformatted_jsons = reformat_node(iterable=partitioned_jsons)
            if not reformatted_jsons:
                logger.info(f"No files to process after {reformat_node.__class__.__name__}")
                return
            partitioned_jsons = reformatted_jsons

        # Copy the final destination to the desired location
        copier = Copier(
            pipeline_context=self.pipeline_context,
        )
        copier(iterable=partitioned_jsons)

        if self.write_node:
            self.write_node(iterable=partitioned_jsons)

        if self.permissions_node:
            self.permissions_node.cleanup_permissions()
