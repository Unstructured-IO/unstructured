import logging
import typing as t

from unstructured.ingest.interfaces import PartitionConfig, ReadConfig
from unstructured.ingest.logger import ingest_log_streaming_init, logger
from unstructured.ingest.processor import process_documents
from unstructured.ingest.runner.utils import update_download_dir_remote_url
from unstructured.ingest.runner.writers import writer_map


def s3(
    read_config: ReadConfig,
    partition_config: PartitionConfig,
    remote_url: str,
    verbose: bool = False,
    recursive: bool = False,
    anonymous: bool = False,
    endpoint_url: t.Optional[str] = None,
    writer_type: t.Optional[str] = None,
    writer_kwargs: t.Optional[dict] = None,
    **kwargs,
):
    writer_kwargs = writer_kwargs if writer_kwargs else {}
    ingest_log_streaming_init(logging.DEBUG if verbose else logging.INFO)

    read_config.download_dir = update_download_dir_remote_url(
        connector_name="s3",
        read_config=read_config,
        remote_url=remote_url,
        logger=logger,
    )

    from unstructured.ingest.connector.s3 import S3SourceConnector, SimpleS3Config

    access_kwargs: t.Dict[str, t.Any] = {"anon": anonymous}
    if endpoint_url:
        access_kwargs["endpoint_url"] = endpoint_url
    source_doc_connector = S3SourceConnector(  # type: ignore
        connector_config=SimpleS3Config(
            path=remote_url,
            recursive=recursive,
            access_kwargs=access_kwargs,
        ),
        read_config=read_config,
        partition_config=partition_config,
    )

    dest_doc_connector = None
    if writer_type:
        writer = writer_map[writer_type]
        dest_doc_connector = writer(**writer_kwargs)

    process_documents(
        source_doc_connector=source_doc_connector,
        partition_config=partition_config,
        verbose=verbose,
        dest_doc_connector=dest_doc_connector,
    )
