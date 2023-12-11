import os

from unstructured.ingest.connector.fsspec.azure import (
    AzureAccessConfig,
    SimpleAzureBlobStorageConfig,
)
from unstructured.ingest.interfaces import (
    PartitionConfig,
    ProcessorConfig,
    ReadConfig,
)
from unstructured.ingest.runner import AzureRunner


def get_connector_config() -> SimpleAzureBlobStorageConfig:
    return SimpleAzureBlobStorageConfig(
        access_config=AzureAccessConfig(
            personal_access_token=os.getenv("AIRTABLE_PERSONAL_ACCESS_TOKEN")
        ),
    )


if __name__ == "__main__":
    runner = AzureRunner(
        processor_config=ProcessorConfig(
            verbose=True,
            output_dir="azure-ingest-output",
            num_processes=2,
        ),
        read_config=ReadConfig(),
        partition_config=PartitionConfig(),
        connector_config=get_connector_config(),
    )
