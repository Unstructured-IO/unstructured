import os

from unstructured.ingest.connector.azure_cognitive_search import (
    AzureCognitiveSearchAccessConfig,
    AzureCognitiveSearchWriteConfig,
    SimpleAzureCognitiveSearchStorageConfig,
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
from unstructured.ingest.runner.writers.azure_cognitive_search import (
    AzureCognitiveSearchWriter,
)
from unstructured.ingest.runner.writers.base_writer import Writer


def get_writer() -> Writer:
    return AzureCognitiveSearchWriter(
        connector_config=SimpleAzureCognitiveSearchStorageConfig(
            access_config=AzureCognitiveSearchAccessConfig(key=os.getenv("AZURE_SEARCH_API_KEY")),
            endpoint=os.getenv("$AZURE_SEARCH_ENDPOINT"),
        ),
        write_config=AzureCognitiveSearchWriteConfig(index="utic-test-ingest-fixtures-output"),
    )


if __name__ == "__main__":
    writer = get_writer()
    runner = LocalRunner(
        processor_config=ProcessorConfig(
            verbose=True,
            output_dir="local-output-to-azure-cog-search",
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
