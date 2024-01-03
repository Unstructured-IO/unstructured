import os

from unstructured.ingest.connector.elasticsearch import (
    ElasticsearchWriteConfig,
)
from unstructured.ingest.connector.local import SimpleLocalConfig
from unstructured.ingest.connector.opensearch import (
    OpenSearchAccessConfig,
    SimpleOpenSearchConfig,
)
from unstructured.ingest.interfaces import (
    ChunkingConfig,
    EmbeddingConfig,
    PartitionConfig,
    ProcessorConfig,
    ReadConfig,
)
from unstructured.ingest.runner import LocalRunner
from unstructured.ingest.runner.writers.base_writer import Writer
from unstructured.ingest.runner.writers.opensearch import (
    OpenSearchWriter,
)


def get_writer() -> Writer:
    return OpenSearchWriter(
        connector_config=SimpleOpenSearchConfig(
            access_config=OpenSearchAccessConfig(
                hosts=os.getenv("OPENSEARCH_HOSTS"),
                username=os.getenv("OPENSEARCH_USERNAME"),
                password=os.getenv("OPENSEARCH_PASSWORD"),
            ),
            index_name=os.getenv("OPENSEARCH_INDEX_NAME"),
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
            output_dir="local-output-to-opensearch",
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
