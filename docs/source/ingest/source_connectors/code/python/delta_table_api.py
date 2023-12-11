import os

from unstructured.ingest.connector.delta_table import SimpleDeltaTableConfig
from unstructured.ingest.interfaces import PartitionConfig, ProcessorConfig, ReadConfig
from unstructured.ingest.runner import DeltaTableRunner

if __name__ == "__main__":
    runner = DeltaTableRunner(
        processor_config=ProcessorConfig(
            verbose=True,
            output_dir="delta-table-example",
            num_processes=2,
        ),
        read_config=ReadConfig(),
        partition_config=PartitionConfig(
            partition_by_api=True,
            api_key=os.getenv("UNSTRUCTURED_API_KEY"),
        ),
        connector_config=SimpleDeltaTableConfig(
            table_uri="s3://utic-dev-tech-fixtures/sample-delta-lake-data/deltatable/",
            storage_options={
                "AWS_REGION": "us-east-2",
                "AWS_ACCESS_KEY_ID": os.getenv("AWS_ACCESS_KEY_ID"),
                "AWS_SECRET_ACCESS_KEY": os.getenv("AWS_SECRET_ACCESS_KEY"),
            },
        ),
    )
    runner.run()
