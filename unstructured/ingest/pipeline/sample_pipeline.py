import os

from unstructured.ingest.connector.s3 import (
    S3SourceConnector,
    SimpleS3Config,
)
from unstructured.ingest.interfaces import (
    EmbeddingConfig,
    PartitionConfig,
    ReadConfig,
)
from unstructured.ingest.pipeline import (
    DocFactory,
    Embedder,
    Partitioner,
    Pipeline,
    PipelineContext,
    Reader,
    Writer,
)
from unstructured.ingest.runner.writers import s3_writer

if __name__ == "__main__":
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
    doc_factory = DocFactory(
        pipeline_config=pipeline_config,
        source_doc_connector=source_doc_connector,
    )
    reader = Reader(pipeline_config=pipeline_config)
    partitioner = Partitioner(pipeline_config=pipeline_config, partition_config=partition_config)
    embedder = Embedder(
        pipeline_config=pipeline_config,
        embedder_config=EmbeddingConfig(api_key=os.getenv("OPENAI_API_KEY")),
    )
    writer = Writer(
        pipeline_config=pipeline_config,
        dest_doc_connector=s3_writer(
            remote_url="s3://utic-dev-tech-fixtures/small-pdf-set/",
            anonymous=True,
        ),
    )
    pipeline = Pipeline(
        verbose=True,
        pipeline_config=pipeline_config,
        doc_factory_node=doc_factory,
        source_node=reader,
        partition_node=partitioner,
        reformat_nodes=[embedder],
        write_node=writer,
    )
    pipeline.run()
