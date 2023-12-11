import os

from unstructured.ingest.connector.fsspec.box import BoxAccessConfig, SimpleBoxConfig
from unstructured.ingest.interfaces import (
    PartitionConfig,
    ProcessorConfig,
    ReadConfig,
)
from unstructured.ingest.runner import BoxRunner

if __name__ == "__main__":
    runner = BoxRunner(
        processor_config=ProcessorConfig(
            verbose=True,
            output_dir="box-output",
            num_processes=2,
        ),
        read_config=ReadConfig(),
        partition_config=PartitionConfig(
            partition_by_api=True,
            api_key=os.getenv("UNSTRUCTURED_API_KEY"),
        ),
        connector_config=SimpleBoxConfig(
            remote_url="box://utic-test-ingest-fixtures",
            recursive=True,
            access_config=BoxAccessConfig(box_app_config=os.getenv("BOX_APP_CONFIG_PATH")),
        ),
    )
    runner.run()
