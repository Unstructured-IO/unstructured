import os

from unstructured.ingest.connector.fsspec.sftp import SftpAccessConfig, SimpleSftpConfig
from unstructured.ingest.interfaces import (
    PartitionConfig,
    ProcessorConfig,
    ReadConfig,
)
from unstructured.ingest.runner import SftpRunner

if __name__ == "__main__":
    runner = SftpRunner(
        processor_config=ProcessorConfig(
            verbose=True,
            output_dir="sftp-output",
            num_processes=2,
        ),
        read_config=ReadConfig(),
        partition_config=PartitionConfig(),
        connector_config=SimpleSftpConfig(
            access_config=SftpAccessConfig(
                username=os.getenv("SFTP_USERNAME"),
                password=os.getenv("SFTP_PASSWORD"),
            ),
            remote_url="sftp://address:port/upload",
            recursive=True,
        ),
    )
    runner.run()
