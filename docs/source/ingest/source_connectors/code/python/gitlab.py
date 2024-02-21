from unstructured.ingest.connector.git import GitAccessConfig
from unstructured.ingest.connector.gitlab import SimpleGitlabConfig
from unstructured.ingest.interfaces import PartitionConfig, ProcessorConfig, ReadConfig
from unstructured.ingest.runner import GitlabRunner

if __name__ == "__main__":
    runner = GitlabRunner(
        processor_config=ProcessorConfig(
            verbose=True,
            output_dir="gitlab-ingest-output",
            num_processes=2,
        ),
        read_config=ReadConfig(),
        partition_config=PartitionConfig(),
        connector_config=SimpleGitlabConfig(
            url="https://gitlab.com/gitlab-com/content-sites/docsy-gitlab",
            branch="v0.0.7",
            access_config=GitAccessConfig(),
        ),
    )
    runner.run()
