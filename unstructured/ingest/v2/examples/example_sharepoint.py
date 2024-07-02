import os
from pathlib import Path

from unstructured.ingest.v2.interfaces import ProcessorConfig
from unstructured.ingest.v2.logger import logger
from unstructured.ingest.v2.pipeline.pipeline import Pipeline
from unstructured.ingest.v2.processes.chunker import ChunkerConfig
from unstructured.ingest.v2.processes.connectors.local import (
    LocalUploaderConfig,
)
from unstructured.ingest.v2.processes.connectors.sharepoint import (
    SharepointAccessConfig,
    SharepointConnectionConfig,
    SharepointDownloaderConfig,
    SharepointIndexerConfig,
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
    Pipeline.from_configs(
        context=ProcessorConfig(work_dir=str(work_dir.resolve()), tqdm=True, verbose=True),
        indexer_config=SharepointIndexerConfig(),
        downloader_config=SharepointDownloaderConfig(download_dir=download_path),
        source_connection_config=SharepointConnectionConfig(
            client_id=os.getenv("SHAREPOINT_CLIENT_ID"),
            site=os.getenv("SHAREPOINT_SITE"),
            access_config=SharepointAccessConfig(client_cred=os.getenv("SHAREPOINT_CRED")),
        ),
        partitioner_config=PartitionerConfig(strategy="fast"),
        chunker_config=ChunkerConfig(chunking_strategy="by_title"),
        embedder_config=EmbedderConfig(embedding_provider="langchain-huggingface"),
        uploader_config=LocalUploaderConfig(output_dir=str(output_path.resolve())),
    ).run()
