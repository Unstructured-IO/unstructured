from unstructured.ingest.connector.notion.connector import NotionAccessConfig, SimpleNotionConfig
from unstructured.ingest.interfaces import PartitionConfig, ProcessorConfig, ReadConfig
from unstructured.ingest.runner import NotionRunner

if __name__ == "__main__":
    runner = NotionRunner(
        processor_config=ProcessorConfig(
            verbose=True,
            output_dir="notion-ingest-output",
            num_processes=2,
        ),
        read_config=ReadConfig(),
        partition_config=PartitionConfig(),
        connector_config=SimpleNotionConfig(
            access_config=NotionAccessConfig(
                notion_api_key="POPULATE API KEY",
            ),
            page_ids=["LIST", "OF", "PAGE", "IDS"],
            database_ids=["LIST", "OF", "DATABASE", "IDS"],
            recursive=False,
        ),
    )
    runner.run()
