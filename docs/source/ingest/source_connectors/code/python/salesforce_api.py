import os

from unstructured.ingest.connector.salesforce import SalesforceAccessConfig, SimpleSalesforceConfig
from unstructured.ingest.interfaces import PartitionConfig, ProcessorConfig, ReadConfig
from unstructured.ingest.runner import SalesforceRunner

if __name__ == "__main__":
    runner = SalesforceRunner(
        processor_config=ProcessorConfig(
            verbose=True,
            output_dir="salesforce-output",
            num_processes=2,
        ),
        read_config=ReadConfig(),
        partition_config=PartitionConfig(
            partition_by_api=True,
            api_key=os.getenv("UNSTRUCTURED_API_KEY"),
        ),
        connector_config=SimpleSalesforceConfig(
            access_config=SalesforceAccessConfig(
                consumer_key=os.getenv("SALESFORCE_CONSUMER_KEY"),
            ),
            username=os.getenv("SALESFORCE_USERNAME"),
            private_key=os.getenv("SALESFORCE_PRIVATE_KEY_PATH"),
            categories=["EmailMessage", "Account", "Lead", "Case", "Campaign"],
            recursive=True,
        ),
    )
    runner.run()
