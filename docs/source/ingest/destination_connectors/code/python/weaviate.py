from unstructured.ingest.connector.local import SimpleLocalConfig
from unstructured.ingest.connector.weaviate import (
    SimpleWeaviateConfig,
    WeaviateAccessConfig,
    WeaviateWriteConfig,
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
from unstructured.ingest.runner.writers.weaviate import (
    WeaviateWriter,
)


def get_writer() -> Writer:
    return WeaviateWriter(
        connector_config=SimpleWeaviateConfig(
            access_config=WeaviateAccessConfig(),
            host_url="http://localhost:8080",
            class_name="elements",
        ),
        write_config=WeaviateWriteConfig(),
    )


if __name__ == "__main__":
    writer = get_writer()
    runner = LocalRunner(
        processor_config=ProcessorConfig(
            verbose=True,
            output_dir="local-output-to-weaviate",
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
