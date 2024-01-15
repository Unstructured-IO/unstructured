import os

from unstructured.ingest.connector.local import SimpleLocalConfig
from unstructured.ingest.connector.mongodb import SimpleMongoDBConfig
from unstructured.ingest.interfaces import (
    ChunkingConfig,
    EmbeddingConfig,
    PartitionConfig,
    ProcessorConfig,
    ReadConfig,
    WriteConfig,
)
from unstructured.ingest.runner import LocalRunner
from unstructured.ingest.runner.writers.base_writer import Writer
from unstructured.ingest.runner.writers.mongodb import (
    MongodbWriter,
)


def get_writer() -> Writer:
    return MongodbWriter(
        connector_config=SimpleMongoDBConfig(
            uri=os.getenv("MONGODB_URI"),
            database=os.getenv("MONGODB_DATABASE_NAME"),
            collection=os.getenv("DESTINATION_MONGO_COLLECTION"),
        ),
        write_config=WriteConfig(),
    )


if __name__ == "__main__":
    writer = get_writer()
    runner = LocalRunner(
        processor_config=ProcessorConfig(
            verbose=True,
            output_dir="local-output-to-mongodb",
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
