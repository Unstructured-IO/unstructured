import os

from unstructured.ingest.connector.jira import JiraAccessConfig, SimpleJiraConfig
from unstructured.ingest.interfaces import PartitionConfig, ProcessorConfig, ReadConfig
from unstructured.ingest.runner import JiraRunner

if __name__ == "__main__":
    runner = JiraRunner(
        processor_config=ProcessorConfig(
            verbose=True,
            output_dir="jira-ingest-output",
            num_processes=2,
        ),
        read_config=ReadConfig(),
        partition_config=PartitionConfig(
            metadata_exclude=["filename", "file_directory", "metadata.data_source.date_processed"],
            partition_by_api=True,
            api_key=os.getenv("UNSTRUCTURED_API_KEY"),
        ),
        connector_config=SimpleJiraConfig(
            access_config=JiraAccessConfig(api_token="ABCDE1234ABDE1234ABCDE1234"),
            url="https://unstructured-jira-connector-test.atlassian.net",
            user_email="12345678@unstructured.io",
        ),
    )
    runner.run()
