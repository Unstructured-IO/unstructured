import os

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
                api_token=os.getenv("CONFLUENCE_API_TOKEN"),
            ),
            user_email=os.getenv("CONFLUENCE_USER_EMAIL"),
            url="https://unstructured-ingest-test.atlassian.net",
        ),
    )
    runner.run()
