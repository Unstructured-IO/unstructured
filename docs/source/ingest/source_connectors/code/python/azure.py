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

if __name__ == "__main__":
    runner = AzureRunner(
        processor_config=ProcessorConfig(
            verbose=True,
            output_dir="azure-ingest-output",
            num_processes=2,
        ),
        read_config=ReadConfig(),
        partition_config=PartitionConfig(),
        connector_config=SimpleAzureBlobStorageConfig(
            access_config=AzureAccessConfig(
                account_name="azureunstructured1",
            ),
            remote_url="abfs://container1/",
        ),
    )
    runner.run()
