import os

from unstructured.ingest.connector.google_drive import (
    GoogleDriveAccessConfig,
    SimpleGoogleDriveConfig,
)
from unstructured.ingest.interfaces import PartitionConfig, ProcessorConfig, ReadConfig
from unstructured.ingest.runner import GoogleDriveRunner

if __name__ == "__main__":
    runner = GoogleDriveRunner(
        processor_config=ProcessorConfig(
            verbose=True,
            output_dir="google-drive-ingest-output",
            num_processes=2,
        ),
        read_config=ReadConfig(),
        partition_config=PartitionConfig(
            partition_by_api=True,
            api_key=os.getenv("UNSTRUCTURED_API_KEY"),
        ),
        connector_config=SimpleGoogleDriveConfig(
            access_config=GoogleDriveAccessConfig(
                service_account_key="POPULATE WITH DRIVE SERVICE ACCOUNT KEY"
            ),
            recursive=True,
            drive_id="POPULATE WITH FILE OR FOLDER ID",
        ),
    )
    runner.run()
