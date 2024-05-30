import os

from unstructured.ingest.connector.git import GitAccessConfig
from unstructured.ingest.connector.github import SimpleGitHubConfig
from unstructured.ingest.interfaces import PartitionConfig, ProcessorConfig, ReadConfig
from unstructured.ingest.runner import GithubRunner

if __name__ == "__main__":
    runner = GithubRunner(
        processor_config=ProcessorConfig(
            verbose=True,
            output_dir="github-ingest-output",
            num_processes=2,
        ),
        read_config=ReadConfig(),
        partition_config=PartitionConfig(
            partition_by_api=True,
            api_key=os.getenv("UNSTRUCTURED_API_KEY"),
        ),
        connector_config=SimpleGitHubConfig(
            url="Unstructured-IO/unstructured", branch="main", access_config=GitAccessConfig()
        ),
    )
    runner.run()
