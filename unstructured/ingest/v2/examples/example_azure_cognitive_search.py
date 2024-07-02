import os
from pathlib import Path

from unstructured.ingest.v2.interfaces import ProcessorConfig
from unstructured.ingest.v2.logger import logger
from unstructured.ingest.v2.pipeline.pipeline import Pipeline
from unstructured.ingest.v2.processes.connectors.azure_cognitive_search import (
    AzureCognitiveSearchAccessConfig,
    AzureCognitiveSearchConnectionConfig,
    AzureCognitiveSearchUploaderConfig,
    AzureCognitiveSearchUploadStagerConfig,
)
from unstructured.ingest.v2.processes.connectors.local import (
    LocalConnectionConfig,
    LocalDownloaderConfig,
    LocalIndexerConfig,
)
from unstructured.ingest.v2.processes.embedder import EmbedderConfig
from unstructured.ingest.v2.processes.partitioner import PartitionerConfig

base_path = Path(__file__).parent.parent.parent.parent.parent
docs_path = base_path / "example-docs"
work_dir = base_path / "tmp_ingest"
output_path = work_dir / "output"
download_path = work_dir / "download"

if __name__ == "__main__":
    logger.info(f"Writing all content in: {work_dir.resolve()}")
    index_name = "ingest-test-destination"
    Pipeline.from_configs(
        context=ProcessorConfig(work_dir=str(work_dir.resolve())),
        indexer_config=LocalIndexerConfig(
            input_path=str(docs_path.resolve()) + "/book-war-and-peace-1p.txt"
        ),
        downloader_config=LocalDownloaderConfig(download_dir=download_path),
        source_connection_config=LocalConnectionConfig(),
        partitioner_config=PartitionerConfig(strategy="fast"),
        # chunker_config=ChunkerConfig(chunking_strategy="by_title"),
        embedder_config=EmbedderConfig(
            embedding_provider="langchain-openai", embedding_api_key=os.getenv("OPENAI_API_KEY")
        ),
        destination_connection_config=AzureCognitiveSearchConnectionConfig(
            access_config=AzureCognitiveSearchAccessConfig(key=os.getenv("AZURE_SEARCH_API_KEY")),
            index=os.getenv("AZURE_SEARCH_INDEX"),
            endpoint=os.getenv("AZURE_SEARCH_ENDPOINT"),
        ),
        uploader_config=AzureCognitiveSearchUploaderConfig(batch_size=10, num_processes=1),
        stager_config=AzureCognitiveSearchUploadStagerConfig(),
    ).run()
