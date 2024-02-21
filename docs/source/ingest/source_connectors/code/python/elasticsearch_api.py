import os

from unstructured.ingest.connector.elasticsearch import (
    ElasticsearchAccessConfig,
    SimpleElasticsearchConfig,
)
from unstructured.ingest.interfaces import PartitionConfig, ProcessorConfig, ReadConfig
from unstructured.ingest.runner import ElasticSearchRunner

if __name__ == "__main__":
    runner = ElasticSearchRunner(
        processor_config=ProcessorConfig(
            verbose=True,
            output_dir="elasticsearch-ingest-output",
            num_processes=2,
        ),
        read_config=ReadConfig(),
        partition_config=PartitionConfig(
            metadata_exclude=["filename", "file_directory", "metadata.data_source.date_processed"],
            partition_by_api=True,
            api_key=os.getenv("UNSTRUCTURED_API_KEY"),
        ),
        connector_config=SimpleElasticsearchConfig(
            access_config=ElasticsearchAccessConfig(hosts=["http://localhost:9200"]),
            index_name="movies",
            fields=["ethnicity", "director", "plot"],
        ),
    )
    runner.run()
