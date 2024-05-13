from pathlib import Path

from unstructured.ingest.v2.interfaces import ProcessorConfig
from unstructured.ingest.v2.pipeline.pipeline import Pipeline
from unstructured.ingest.v2.processes.chunker import Chunker, ChunkerConfig
from unstructured.ingest.v2.processes.connectors.local import (
    LocalDestination,
    LocalIndexer,
    LocalIndexerConfig,
    LocalSource,
    LocalUploader,
    LocalUploaderConfig,
)
from unstructured.ingest.v2.processes.embedder import Embedder, EmbedderConfig
from unstructured.ingest.v2.processes.partitioner import Partitioner, PartitionerConfig

base_path = Path(__file__).parent.parent.parent.parent
docs_path = base_path / "example-docs"
work_dir = base_path / "tmp_ingest"
output_path = work_dir / "output"

if __name__ == "__main__":
    source = LocalSource(
        indexer=LocalIndexer(
            index_config=LocalIndexerConfig(
                input_directory=str(docs_path),
                file_glob=["*.pdf"],
            )
        ),
    )
    partitioner = Partitioner(config=PartitionerConfig(strategy="fast"))
    chunker = Chunker(config=ChunkerConfig(chunking_strategy="by_title"))
    embedder = Embedder(config=EmbedderConfig(provider="langchain-huggingface"))
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
