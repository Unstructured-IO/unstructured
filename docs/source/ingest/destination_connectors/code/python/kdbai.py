import os

from unstructured.ingest.connector.kdbai import (
    KDBAIAccessConfig,
    KDBAIWriteConfig,
    SimpleKDBAIConfig,
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
from unstructured.ingest.runner.writers.kdbai import (
    KDBAIWriter,
)


def get_writer() -> Writer:
    return KDBAIWriter(
        connector_config=SimpleKDBAIConfig(
            access_config=KDBAIAccessConfig(api_key=os.getenv("KDBAI_API_KEY")),
            endpoint="http://localhost:8082",
            table_name="elements",
        ),
        write_config=KDBAIWriteConfig(),
    )


if __name__ == "__main__":
    writer = get_writer()
    runner = LocalRunner(
        processor_config=ProcessorConfig(
            verbose=True,
            output_dir="local-output-to-kdbai",
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
