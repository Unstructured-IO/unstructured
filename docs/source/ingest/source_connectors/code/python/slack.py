from unstructured.ingest.connector.slack import SimpleSlackConfig, SlackAccessConfig
from unstructured.ingest.interfaces import PartitionConfig, ProcessorConfig, ReadConfig
from unstructured.ingest.runner import SlackRunner

if __name__ == "__main__":
    runner = SlackRunner(
        processor_config=ProcessorConfig(
            verbose=True,
            output_dir="slack-ingest-download",
            num_processes=2,
        ),
        read_config=ReadConfig(),
        partition_config=PartitionConfig(),
        connector_config=SimpleSlackConfig(
            access_config=SlackAccessConfig(
                token="12345678",
            ),
            channels=["12345678"],
            start_date="2023-04-01T01:00:00-08:00",
            end_date="2023-04-02,",
        ),
    )
    runner.run()
