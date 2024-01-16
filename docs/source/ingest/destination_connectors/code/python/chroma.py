from unstructured.ingest.connector.chroma import (
    ChromaAccessConfig,
    ChromaWriteConfig,
    SimpleChromaConfig,
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
from unstructured.ingest.runner.writers.chroma import (
    ChromaWriter,
)


def get_writer() -> Writer:
    return ChromaWriter(
        connector_config=SimpleChromaConfig(
            access_config=ChromaAccessConfig(),
            host="localhost",
            port=8000,
            collection_name="elements",
            tenant="default_tenant",
            database="default_database",
        ),
        write_config=ChromaWriteConfig(),
    )


if __name__ == "__main__":
    writer = get_writer()
    runner = LocalRunner(
        processor_config=ProcessorConfig(
            verbose=True,
            output_dir="local-output-to-chroma",
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
