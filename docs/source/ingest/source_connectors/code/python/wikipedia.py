from unstructured.ingest.connector.wikipedia import SimpleWikipediaConfig
from unstructured.ingest.interfaces import PartitionConfig, ProcessorConfig, ReadConfig
from unstructured.ingest.runner import WikipediaRunner

if __name__ == "__main__":
    runner = WikipediaRunner(
        processor_config=ProcessorConfig(
            verbose=True,
            output_dir="wikipedia-ingest-output",
            num_processes=2,
        ),
        read_config=ReadConfig(),
        partition_config=PartitionConfig(),
        connector_config=SimpleWikipediaConfig(
            page_title="Open Source Software",
            auto_suggest=False,
        ),
    )
    runner.run()
