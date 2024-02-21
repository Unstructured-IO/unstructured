import os

from unstructured.ingest.connector.fsspec.s3 import S3AccessConfig, SimpleS3Config
from unstructured.ingest.interfaces import (
    PartitionConfig,
    ProcessorConfig,
    ReadConfig,
)
from unstructured.ingest.runner import S3Runner

if __name__ == "__main__":
    runner = S3Runner(
        processor_config=ProcessorConfig(
            verbose=True,
            output_dir="s3-small-batch-output",
            num_processes=2,
        ),
        read_config=ReadConfig(),
        partition_config=PartitionConfig(
            partition_by_api=True,
            api_key=os.getenv("UNSTRUCTURED_API_KEY"),
        ),
        connector_config=SimpleS3Config(
            access_config=S3AccessConfig(
                anon=True,
            ),
            remote_url="s3://utic-dev-tech-fixtures/small-pdf-set/",
        ),
    )
    runner.run()
