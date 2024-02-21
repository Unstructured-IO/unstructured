from unstructured.ingest.connector.confluence import ConfluenceAccessConfig, SimpleConfluenceConfig
from unstructured.ingest.interfaces import PartitionConfig, ProcessorConfig, ReadConfig
from unstructured.ingest.runner import ConfluenceRunner

if __name__ == "__main__":
    runner = ConfluenceRunner(
        processor_config=ProcessorConfig(
            verbose=True,
            output_dir="confluence-ingest-output",
            num_processes=2,
        ),
        read_config=ReadConfig(),
        partition_config=PartitionConfig(
            metadata_exclude=["filename", "file_directory", "metadata.data_source.date_processed"],
        ),
        connector_config=SimpleConfluenceConfig(
            access_config=ConfluenceAccessConfig(
                api_token="ABCDE1234ABDE1234ABCDE1234",
            ),
            user_email="12345678@unstructured.io",
            url="https://unstructured-ingest-test.atlassian.net",
        ),
    )
    runner.run()
