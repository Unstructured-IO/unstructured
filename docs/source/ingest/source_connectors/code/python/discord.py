import os

from unstructured.ingest.connector.discord import DiscordAccessConfig, SimpleDiscordConfig
from unstructured.ingest.interfaces import PartitionConfig, ProcessorConfig, ReadConfig
from unstructured.ingest.runner import DiscordRunner

if __name__ == "__main__":
    runner = DiscordRunner(
        processor_config=ProcessorConfig(
            verbose=True,
            output_dir="discord-ingest-example",
            num_processes=2,
        ),
        read_config=ReadConfig(),
        partition_config=PartitionConfig(),
        connector_config=SimpleDiscordConfig(
            access_config=DiscordAccessConfig(token=os.getenv("DISCORD_TOKEN")),
            channels=["12345678"],
        ),
    )
    runner.run()
