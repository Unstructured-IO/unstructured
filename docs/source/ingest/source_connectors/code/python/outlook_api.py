import os

from unstructured.ingest.connector.outlook import OutlookAccessConfig, SimpleOutlookConfig
from unstructured.ingest.interfaces import PartitionConfig, ProcessorConfig, ReadConfig
from unstructured.ingest.runner import OutlookRunner

if __name__ == "__main__":
    runner = OutlookRunner(
        processor_config=ProcessorConfig(
            verbose=True,
            output_dir="outlook-output",
            num_processes=2,
        ),
        read_config=ReadConfig(),
        partition_config=PartitionConfig(
            partition_by_api=True,
            api_key=os.getenv("UNSTRUCTURED_API_KEY"),
        ),
        connector_config=SimpleOutlookConfig(
            access_config=OutlookAccessConfig(
                client_credential=os.getenv("MS_CLIENT_CRED"),
            ),
            client_id=os.getenv("MS_CLIENT_ID"),
            tenant=os.getenv("MS_TENANT_ID"),
            user_email=os.getenv("MS_USER_EMAIL"),
            outlook_folders=["Inbox", "Sent Items"],
            recursive=True,
        ),
    )
    runner.run()
