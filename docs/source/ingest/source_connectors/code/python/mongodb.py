import os

from unstructured.ingest.connector.mongodb import (
    SimpleMongoDBConfig,
)
from unstructured.ingest.interfaces import PartitionConfig, ProcessorConfig, ReadConfig
from unstructured.ingest.runner import MongoDBRunner

if __name__ == "__main__":
    runner = MongoDBRunner(
        processor_config=ProcessorConfig(
            verbose=True,
            output_dir="mongodb-ingest-output",
            num_processes=2,
        ),
        read_config=ReadConfig(),
        partition_config=PartitionConfig(
            metadata_exclude=["filename", "file_directory", "metadata.data_source.date_processed"],
        ),
        connector_config=SimpleMongoDBConfig(
            uri=os.getenv("MONGODB_URI"),
            database=os.getenv("MONGODB_DATABASE_NAME"),
            collection=os.getenv("DESTINATION_MONGO_COLLECTION"),
        ),
    )
    runner.run()
