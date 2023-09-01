import logging
import typing as t

from unstructured.ingest.interfaces2 import PartitionConfig, ReadConfig
from unstructured.ingest.logger import ingest_log_streaming_init, logger
from unstructured.ingest.processor2 import process_documents
from unstructured.ingest.runner.utils2 import update_download_dir_remote_url
from unstructured.ingest.runner.writers import writer_map


def s3(
    verbose: bool,
    read_config: ReadConfig,
    partition_configs: PartitionConfig,
    remote_url: str,
    recursive: bool,
    anonymous: bool,
    writer_type: t.Optional[str] = None,
    writer_kwargs: t.Optional[dict] = None,
    **kwargs,
):
    writer_kwargs = writer_kwargs if writer_kwargs else {}
    ingest_log_streaming_init(logging.DEBUG if verbose else logging.INFO)

    read_config.download_dir = update_download_dir_remote_url(
        connector_name="s3",
        read_configs=read_config,
        remote_url=remote_url,
        logger=logger,
    )

    from unstructured.ingest.connector.s3_2 import S3SourceConnector, SimpleS3Config

    source_doc_connector = S3SourceConnector(  # type: ignore
        read_config=read_config,
        connector_config=SimpleS3Config(
            path=remote_url,
            recursive=recursive,
            access_kwargs={"anon": anonymous},
        ),
        partition_config=partition_configs,
    )

    dest_doc_connector = None
    if writer_type:
        writer = writer_map[writer_type]
        print(f"WRITER CONFIGS: {writer_kwargs}")
        dest_doc_connector = writer(**writer_kwargs)

    process_documents(
        source_doc_connector=source_doc_connector,
        partition_config=partition_configs,
        verbose=verbose,
        dest_doc_connector=dest_doc_connector,
    )
