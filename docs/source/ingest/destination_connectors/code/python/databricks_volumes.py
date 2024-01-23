import os

from unstructured.ingest.connector.databricks_volumes import (
    DatabricksVolumesAccessConfig,
    DatabricksVolumesWriteConfig,
    SimpleDatabricksVolumesConfig,
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
from unstructured.ingest.runner.writers.databricks_volumes import (
    DatabricksVolumesWriter,
)


def get_writer() -> Writer:
    return DatabricksVolumesWriter(
        connector_config=SimpleDatabricksVolumesConfig(
            host=os.getenv("DATABRICKS_HOST"),
            access_config=DatabricksVolumesAccessConfig(
                username=os.getenv("DATABRICKS_USERNAME"), password=os.getenv("DATABRICKS_PASSWORD")
            ),
        ),
        write_config=DatabricksVolumesWriteConfig(
            catalog=os.getenv("DATABRICKS_CATALOG"),
            volume=os.getenv("DATABRICKS_VOLUME"),
        ),
    )


if __name__ == "__main__":
    writer = get_writer()
    runner = LocalRunner(
        processor_config=ProcessorConfig(
            verbose=True,
            output_dir="local-output-to-databricks-volumes",
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
