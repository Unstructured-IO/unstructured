import os

from unstructured.ingest.connector.fsspec.dropbox import (
    DropboxAccessConfig,
    DropboxWriteConfig,
    SimpleDropboxConfig,
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
from unstructured.ingest.runner.writers.fsspec.dropbox import (
    DropboxWriter,
)


def get_writer() -> Writer:
    return DropboxWriter(
        connector_config=SimpleDropboxConfig(
            access_config=DropboxAccessConfig(token=os.getenv("DROPBOX_TOKEN")),
            remote_url="dropbox://unstructured/war-and-peace-output",
        ),
        write_config=DropboxWriteConfig(),
    )


if __name__ == "__main__":
    writer = get_writer()
    runner = LocalRunner(
        processor_config=ProcessorConfig(
            verbose=True,
            output_dir="local-output-to-dropbox",
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
