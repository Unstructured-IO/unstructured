import os

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
        partition_config=PartitionConfig(),
    )
    runner.run(
        client_id=os.getenv("MS_CLIENT_ID"),
        client_cred=os.getenv("MS_CLIENT_CRED"),
        tenant=os.getenv("MS_TENANT_ID"),
        user_email=os.getenv("MS_USER_EMAIL"),
        outlook_folders=["Inbox", "Sent Items"],
        recursive=True,
    )
