import os

from unstructured.ingest.interfaces import PartitionConfig, ProcessorConfig, ReadConfig
from unstructured.ingest.runner import LocalRunner

if __name__ == "__main__":
    runner = LocalRunner(
        processor_config=ProcessorConfig(
            verbose=True,
            output_dir="local-output-to-postgres",
            num_processes=2,
        ),
        read_config=ReadConfig(),
        partition_config=PartitionConfig(),
        writer_type="sql",
        writer_kwargs={
            "db_type": os.getenv("DB_TYPE"),
            "username": os.getenv("USERNAME"),
            "password": os.getenv("DB_PASSWORD"),
            "host": os.getenv("DB_HOST"),
            "port": os.getenv("DB_PORT"),
            "database": os.getenv("DB_DATABASE"),
        },
    )
    runner.run(
        input_path="example-docs/fake-memo.pdf",
    )
