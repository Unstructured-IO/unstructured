from pathlib import Path

from unstructured.ingest.v2.interfaces import ProcessorConfig
from unstructured.ingest.v2.pipeline.pipeline import Pipeline
from unstructured.ingest.v2.processes.chunker import Chunker, ChunkerConfig
from unstructured.ingest.v2.processes.connectors.fsspec.s3 import (
    S3ConnectionConfig,
    S3Downloader,
    S3DownloaderConfig,
    S3Indexer,
    S3IndexerConfig,
    S3Source,
)
from unstructured.ingest.v2.processes.connectors.local import (
    LocalDestination,
    LocalUploader,
    LocalUploaderConfig,
)
from unstructured.ingest.v2.processes.embedder import Embedder, EmbedderConfig
from unstructured.ingest.v2.processes.partitioner import Partitioner, PartitionerConfig

base_path = Path(__file__).parent.parent.parent.parent
docs_path = base_path / "example-docs"
work_dir = base_path / "tmp_ingest"
output_path = work_dir / "output"
download_path = work_dir / "download"

if __name__ == "__main__":
    connection_config = S3ConnectionConfig(anonymous=True)
    source = S3Source(
        indexer=S3Indexer(
            index_config=S3IndexerConfig(remote_url="s3://utic-dev-tech-fixtures/small-pdf-set/"),
            connection_config=connection_config,
        ),
        downloader=S3Downloader(
            download_config=S3DownloaderConfig(download_dir=download_path),
            connection_config=connection_config,
        ),
    )
    partitioner = Partitioner(config=PartitionerConfig(strategy="fast"))
    chunker = Chunker(config=ChunkerConfig(chunking_strategy="by_title"))
    embedder = Embedder(config=EmbedderConfig(embedding_provider="langchain-huggingface"))
    destination = LocalDestination(
        uploader=LocalUploader(
            upload_config=LocalUploaderConfig(output_directory=str(output_path.resolve()))
        )
    )
    pipeline = Pipeline(
        context=ProcessorConfig(work_dir=str(work_dir.resolve())),
        indexer=source.indexer,
        downloader=source.downloader,
        partitioner=partitioner,
        chunker=chunker,
        embedder=embedder,
        uploader=destination.uploader,
    )
    pipeline.run()
