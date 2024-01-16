import os

from unstructured.ingest.connector.local import SimpleLocalConfig
from unstructured.ingest.connector.vectara import (
    SimpleVectaraConfig,
    VectaraAccessConfig,
    WriteConfig,
)
from unstructured.ingest.interfaces import (
    PartitionConfig,
    ProcessorConfig,
    ReadConfig,
)
from unstructured.ingest.runner import LocalRunner
from unstructured.ingest.runner.writers.base_writer import Writer
from unstructured.ingest.runner.writers.vectara import (
    VectaraWriter,
)


def get_writer() -> Writer:
    return VectaraWriter(
        connector_config=SimpleVectaraConfig(
            access_config=VectaraAccessConfig(
                oauth_client_id=os.getenv("VECTARA_OAUTH_CLIENT_ID"),
                oauth_secret=os.getenv("VECTARA_OAUTH_SECRET"),
            ),
            customer_id=os.getenv("VECTARA_CUSTOMER_ID"),
            corpus_name="test-corpus-vectara",
        ),
        write_config=WriteConfig(),
    )


if __name__ == "__main__":
    writer = get_writer()
    runner = LocalRunner(
        processor_config=ProcessorConfig(
            verbose=True,
            output_dir="local-output-to-vectara",
            num_processes=2,
        ),
        connector_config=SimpleLocalConfig(
            input_path="example-docs/book-war-and-peace-1225p.txt",
        ),
        read_config=ReadConfig(),
        partition_config=PartitionConfig(),
        # chunking_config=ChunkingConfig(chunk_elements=True),
        writer=writer,
        writer_kwargs={},
    )
    runner.run()
