from pathlib import Path

from unstructured.ingest.v2.interfaces import ProcessorConfig
from unstructured.ingest.v2.logger import logger
from unstructured.ingest.v2.pipeline.pipeline import Pipeline
from unstructured.ingest.v2.processes.chunker import ChunkerConfig
from unstructured.ingest.v2.processes.connectors.fsspec.s3 import (
    S3ConnectionConfig,
    S3DownloaderConfig,
    S3IndexerConfig,
)
from unstructured.ingest.v2.processes.connectors.local import (
    LocalUploaderConfig,
)
from unstructured.ingest.v2.processes.embedder import EmbedderConfig
from unstructured.ingest.v2.processes.partitioner import PartitionerConfig

base_path = Path(__file__).parent.parent.parent.parent
docs_path = base_path / "example-docs"
work_dir = base_path / "tmp_ingest"
output_path = work_dir / "output"
download_path = work_dir / "download"

if __name__ == "__main__":
    logger.info(f"Writing all content in: {work_dir.resolve()}")
    Pipeline.from_configs(
        context=ProcessorConfig(
            work_dir=str(work_dir.resolve()), tqdm=True, reprocess=True, verbose=True
        ),
        indexer_config=S3IndexerConfig(remote_url="s3://utic-dev-tech-fixtures/small-pdf-set/"),
        downloader_config=S3DownloaderConfig(download_dir=download_path),
        source_connection_config=S3ConnectionConfig(anonymous=True),
        partitioner_config=PartitionerConfig(strategy="fast"),
        chunker_config=ChunkerConfig(chunking_strategy="by_title"),
        embedder_config=EmbedderConfig(embedding_provider="langchain-huggingface"),
        uploader_config=LocalUploaderConfig(output_dir=str(output_path.resolve())),
    ).run()
