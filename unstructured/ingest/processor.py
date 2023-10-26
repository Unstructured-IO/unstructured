import multiprocessing as mp
import typing as t
from contextlib import suppress

from unstructured.ingest.interfaces import (
    BaseDestinationConnector,
    BaseSourceConnector,
    ChunkingConfig,
    EmbeddingConfig,
    PartitionConfig,
    PermissionsConfig,
    ProcessorConfig,
    RetryStrategyConfig,
)
from unstructured.ingest.pipeline import (
    Chunker,
    DocFactory,
    Embedder,
    Partitioner,
    PermissionsDataCleaner,
    Pipeline,
    PipelineContext,
    Reader,
    ReformatNode,
    Writer,
)

with suppress(RuntimeError):
    mp.set_start_method("spawn")


def process_documents(
    processor_config: ProcessorConfig,
    source_doc_connector: BaseSourceConnector,
    partition_config: PartitionConfig,
    dest_doc_connector: t.Optional[BaseDestinationConnector] = None,
    chunking_config: t.Optional[ChunkingConfig] = None,
    embedder_config: t.Optional[EmbeddingConfig] = None,
    permissions_config: t.Optional[PermissionsConfig] = None,
    retry_strategy_config: t.Optional[RetryStrategyConfig] = None,
) -> None:
    pipeline_config = PipelineContext.from_dict(processor_config.to_dict())
    doc_factory = DocFactory(
        pipeline_context=pipeline_config,
        source_doc_connector=source_doc_connector,
    )
    reader = Reader(
        pipeline_context=pipeline_config,
        retry_strategy_config=retry_strategy_config,
        read_config=source_doc_connector.read_config,
    )
    partitioner = Partitioner(pipeline_context=pipeline_config, partition_config=partition_config)
    reformat_nodes: t.List[ReformatNode] = []
    if chunking_config:
        reformat_nodes.append(
            Chunker(
                pipeline_context=pipeline_config,
                chunking_config=chunking_config,
            ),
        )
    if embedder_config:
        reformat_nodes.append(
            Embedder(
                pipeline_context=pipeline_config,
                embedder_config=embedder_config,
            ),
        )
    writer = (
        Writer(
            pipeline_context=pipeline_config,
            dest_doc_connector=dest_doc_connector,
        )
        if dest_doc_connector
        else None
    )
    permissions_data_cleaner = (
        PermissionsDataCleaner(pipeline_context=pipeline_config, processor_config=processor_config)
        if permissions_config
        else None
    )
    pipeline = Pipeline(
        pipeline_context=pipeline_config,
        doc_factory_node=doc_factory,
        source_node=reader,
        partition_node=partitioner,
        reformat_nodes=reformat_nodes,
        write_node=writer,
        permissions_node=permissions_data_cleaner,
    )
    pipeline.run()
