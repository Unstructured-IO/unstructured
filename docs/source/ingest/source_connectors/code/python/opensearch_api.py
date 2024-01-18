import os

from unstructured.ingest.connector.opensearch import (
    OpenSearchAccessConfig,
    SimpleOpenSearchConfig,
)
from unstructured.ingest.interfaces import PartitionConfig, ProcessorConfig, ReadConfig
from unstructured.ingest.runner import OpenSearchRunner

if __name__ == "__main__":
    runner = OpenSearchRunner(
        processor_config=ProcessorConfig(
            verbose=True,
            output_dir="opensearch-ingest-output",
            num_processes=2,
        ),
        read_config=ReadConfig(),
        partition_config=PartitionConfig(
            metadata_exclude=["filename", "file_directory", "metadata.data_source.date_processed"],
            partition_by_api=True,
            api_key=os.getenv("UNSTRUCTURED_API_KEY"),
        ),
        connector_config=SimpleOpenSearchConfig(
            access_config=OpenSearchAccessConfig(hosts=["http://localhost:9200"]),
            index_name="movies",
            fields=["ethnicity", "director", "plot"],
        ),
    )
    runner.run()
