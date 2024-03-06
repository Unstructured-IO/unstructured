import os

from unstructured.ingest.connector.astra import (
    AstraAccessConfig,
    AstraWriteConfig,
    SimpleAstraConfig,
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
from unstructured.ingest.runner.writers.astra import (
    AstraWriter,
)
from unstructured.ingest.runner.writers.base_writer import Writer


def get_writer() -> Writer:
    return AstraWriter(
        connector_config=SimpleAstraConfig(
            access_config=AstraAccessConfig(
                token=os.getenv("ASTRA_DB_TOKEN"), api_endpoint=os.getenv("ASTRA_DB_ENDPOINT")
            ),
            collection_name="test_collection",
            embedding_dimension=384,
        ),
        write_config=AstraWriteConfig(batch_size=80),
    )


if __name__ == "__main__":
    writer = get_writer()
    runner = LocalRunner(
        processor_config=ProcessorConfig(
            verbose=True,
            output_dir="local-output-to-astra",
            num_processes=2,
        ),
        connector_config=SimpleLocalConfig(
            input_path="example-docs/book-war-and-peace-1p.txt",
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
