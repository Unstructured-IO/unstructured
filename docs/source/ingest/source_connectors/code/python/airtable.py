import os

from unstructured.ingest.connector.airtable import AirtableAccessConfig, SimpleAirtableConfig
from unstructured.ingest.interfaces import (
    PartitionConfig,
    ProcessorConfig,
    ReadConfig,
)
from unstructured.ingest.runner import AirtableRunner

if __name__ == "__main__":
    runner = AirtableRunner(
        processor_config=ProcessorConfig(
            verbose=True,
            output_dir="airtable-ingest-output",
            num_processes=2,
        ),
        read_config=ReadConfig(),
        partition_config=PartitionConfig(),
        connector_config=SimpleAirtableConfig(
            access_config=AirtableAccessConfig(
                personal_access_token=os.getenv("AIRTABLE_PERSONAL_ACCESS_TOKEN")
            ),
        ),
    )
    runner.run()
