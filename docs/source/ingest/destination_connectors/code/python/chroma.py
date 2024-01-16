from unstructured.ingest.interfaces import (
    ChunkingConfig,
    EmbeddingConfig,
    PartitionConfig,
    ProcessorConfig,
    ReadConfig,
)
from unstructured.ingest.runner import LocalRunner

if __name__ == "__main__":
    runner = LocalRunner(
        processor_config=ProcessorConfig(
            verbose=True,
            output_dir="local-output-to-chroma",
            num_processes=2,
        ),
        read_config=ReadConfig(),
        partition_config=PartitionConfig(),
        chunking_config=ChunkingConfig(chunk_elements=True),
        embedding_config=EmbeddingConfig(
            provider="langchain-huggingface",
        ),
        writer_type="chroma",
        writer_kwargs={
            "host": "localhost",
            "port": 8000,
            "collection_name": "test-collection",
            "batch_size": 80,
        },
    )
    runner.run(
        input_path="example-docs/fake-memo.pdf",
    )
