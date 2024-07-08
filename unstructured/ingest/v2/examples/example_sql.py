import os
import sqlite3
from pathlib import Path

from unstructured.ingest.v2.interfaces import ProcessorConfig
from unstructured.ingest.v2.logger import logger
from unstructured.ingest.v2.pipeline.pipeline import Pipeline
from unstructured.ingest.v2.processes.chunker import ChunkerConfig
from unstructured.ingest.v2.processes.connectors.local import (
    LocalConnectionConfig,
    LocalDownloaderConfig,
    LocalIndexerConfig,
)
from unstructured.ingest.v2.processes.connectors.sql import (
    DatabaseType,
    SimpleSqlConfig,
    SQLAccessConfig,
    SQLUploaderConfig,
    SQLUploadStagerConfig,
)
from unstructured.ingest.v2.processes.embedder import EmbedderConfig
from unstructured.ingest.v2.processes.partitioner import PartitionerConfig

base_path = Path(__file__).parent.parent.parent.parent.parent
docs_path = base_path / "example-docs"
work_dir = base_path / "tmp_ingest"
output_path = work_dir / "output"
download_path = work_dir / "download"

SQLITE_DB = "test-sql-db.sqlite"

if __name__ == "__main__":
    logger.info(f"Writing all content in: {work_dir.resolve()}")

    configs = {
        "context": ProcessorConfig(work_dir=str(work_dir.resolve())),
        "indexer_config": LocalIndexerConfig(input_path=str(docs_path.resolve()) + "/multisimple/"),
        "downloader_config": LocalDownloaderConfig(download_dir=download_path),
        "source_connection_config": LocalConnectionConfig(),
        "partitioner_config": PartitionerConfig(strategy="fast"),
        "chunker_config": ChunkerConfig(
            chunking_strategy="by_title",
            chunk_include_orig_elements=False,
            chunk_max_characters=1500,
            chunk_multipage_sections=True,
        ),
        "embedder_config": EmbedderConfig(embedding_provider="langchain-huggingface"),
        "stager_config": SQLUploadStagerConfig(),
        "uploader_config": SQLUploaderConfig(batch_size=10),
    }

    if os.path.exists(SQLITE_DB):
        os.remove(SQLITE_DB)

    connection = sqlite3.connect(database=SQLITE_DB)

    query = None
    script_path = (
        Path(__file__).parent.parent.parent.parent.parent
        / Path("scripts/sql-test-helpers/create-sqlite-schema.sql")
    ).resolve()
    with open(script_path) as f:
        query = f.read()
    cursor = connection.cursor()
    cursor.executescript(query)
    connection.close()

    # sqlite test first
    Pipeline.from_configs(
        destination_connection_config=SimpleSqlConfig(
            db_type=DatabaseType.SQLITE,
            database=SQLITE_DB,
            access_config=SQLAccessConfig(),
        ),
        **configs,
    ).run()

    # now, pg with pgvector
    Pipeline.from_configs(
        destination_connection_config=SimpleSqlConfig(
            db_type=DatabaseType.POSTGRESQL,
            database="elements",
            host="localhost",
            port=5433,
            access_config=SQLAccessConfig(username="unstructured", password="test"),
        ),
        **configs,
    ).run()
