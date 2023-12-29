import os

from unstructured.ingest.connector.elasticsearch import (
    ElasticsearchAccessConfig,
    ElasticsearchWriteConfig,
    SimpleElasticsearchConfig,
)
from unstructured.ingest.connector.local import SimpleLocalConfig
from unstructured.ingest.interfaces import (
    ChunkingConfig,
    EmbeddingConfig,
    PartitionConfig,
    ProcessorConfig,
    ReadConfig,
)
from unstructured.ingest.runner import LocalRunner
from unstructured.ingest.runner.writers.base_writer import Writer
from unstructured.ingest.runner.writers.elasticsearch import (
    ElasticsearchWriter,
)


def get_writer() -> Writer:
    return ElasticsearchWriter(
        connector_config=SimpleElasticsearchConfig(
            access_config=ElasticsearchAccessConfig(
                hosts=os.getenv("ELASTICSEARCH_HOSTS"),
                username=os.getenv("ELASTICSEARCH_USERNAME"),
                password=os.getenv("ELASTICSEARCH_PASSWORD"),
            ),
            index_name=os.getenv("ELASTICSEARCH_INDEX_NAME"),
        ),
        write_config=ElasticsearchWriteConfig(
            batch_size_bytes=15_000_000,
            num_processes=2,
        ),
    )


if __name__ == "__main__":
    writer = get_writer()
    runner = LocalRunner(
        processor_config=ProcessorConfig(
            verbose=True,
            output_dir="local-output-to-elasticsearch",
            num_processes=2,
        ),
        connector_config=SimpleLocalConfig(
            input_path="example-docs/book-war-and-peace-1225p.txt",
        ),
        read_config=ReadConfig(),
        partition_config=PartitionConfig(),
        chunking_config=ChunkingConfig(chunk_elements=True),
        embedding_config=EmbeddingConfig(
            provider="langchain-huggingface",
        ),
        writer=writer,
        writer_kwargs={},
    )
    runner.run()
