import os

from unstructured.ingest.connector.local import SimpleLocalConfig
from unstructured.ingest.interfaces import PartitionConfig, ProcessorConfig, ReadConfig
from unstructured.ingest.runner import LocalRunner

if __name__ == "__main__":
    runner = LocalRunner(
        processor_config=ProcessorConfig(
            verbose=True,
            output_dir="local-ingest-output",
            num_processes=2,
        ),
        read_config=ReadConfig(),
        partition_config=PartitionConfig(
            partition_by_api=True,
            api_key=os.getenv("UNSTRUCTURED_API_KEY"),
        ),
        connector_config=SimpleLocalConfig(
            input_path="example-docs",
            recursive=True,
        ),
    )
    runner.run()
