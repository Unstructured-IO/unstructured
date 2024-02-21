import os

from unstructured.ingest.connector.clarifai import (
    ClarifaiAccessConfig,
    ClarifaiWriteConfig,
    SimpleClarifaiConfig,
)
from unstructured.ingest.connector.local import SimpleLocalConfig
from unstructured.ingest.interfaces import (
    ChunkingConfig,
    PartitionConfig,
    ProcessorConfig,
    ReadConfig,
)
from unstructured.ingest.runner import LocalRunner
from unstructured.ingest.runner.writers.base_writer import Writer
from unstructured.ingest.runner.writers.clarifai import (
    ClarifaiWriter,
)

def get_writer() -> Writer:
    return ClarifaiWriter(
        connector_config=SimpleClarifaiConfig(
            access_config=ClarifaiAccessConfig(
                api_key= "CLARIFAI_PAT"
            ),
            app_id= "CLARIFAI_APP",
            user_id= "CLARIFAI_USER_ID"
            ),
        write_config=ClarifaiWriteConfig()
    )

if __name__ == "__main__":
    writer = get_writer()
    runner = LocalRunner(
        processor_config=ProcessorConfig(
            verbose=True,
            output_dir="local-output-to-clarifai-app",
            num_processes=2,
        ),
        connector_config=SimpleLocalConfig(
            input_path="example-docs/book-war-and-peace-1225p.txt",
        ),
        read_config=ReadConfig(),
        partition_config=PartitionConfig(),
        chunking_config=ChunkingConfig(chunk_elements=True),
        writer=writer,
        writer_kwargs={},
    )
    runner.run()
