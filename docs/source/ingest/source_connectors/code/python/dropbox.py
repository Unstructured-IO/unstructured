import os

from unstructured.ingest.connector.fsspec.dropbox import DropboxAccessConfig, SimpleDropboxConfig
from unstructured.ingest.interfaces import (
    PartitionConfig,
    ProcessorConfig,
    ReadConfig,
)
from unstructured.ingest.runner import DropboxRunner

if __name__ == "__main__":
    runner = DropboxRunner(
        processor_config=ProcessorConfig(
            verbose=True,
            output_dir="dropbox-output",
            num_processes=2,
        ),
        read_config=ReadConfig(),
        partition_config=PartitionConfig(),
        connector_config=SimpleDropboxConfig(
            access_config=DropboxAccessConfig(token=os.getenv("DROPBOX_ACCESS_TOKEN")),
            remote_url="dropbox:// /",
            recursive=True,
        ),
    )
    runner.run()
