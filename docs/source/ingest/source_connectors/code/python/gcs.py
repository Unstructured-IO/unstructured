from unstructured.ingest.connector.fsspec.gcs import GcsAccessConfig, SimpleGcsConfig
from unstructured.ingest.interfaces import (
    PartitionConfig,
    ProcessorConfig,
    ReadConfig,
)
from unstructured.ingest.runner import GCSRunner

if __name__ == "__main__":
    runner = GCSRunner(
        processor_config=ProcessorConfig(
            verbose=True,
            output_dir="gcs-output",
            num_processes=2,
        ),
        read_config=ReadConfig(),
        partition_config=PartitionConfig(),
        connector_config=SimpleGcsConfig(
            access_config=GcsAccessConfig(),
            remote_url="gs://utic-test-ingest-fixtures-public/",
            recursive=True,
        ),
    )
    runner.run()
