import hashlib
import logging
import typing as t

from unstructured.ingest.interfaces import PartitionConfig, ReadConfig
from unstructured.ingest.logger import ingest_log_streaming_init, logger
from unstructured.ingest.processor import process_documents
from unstructured.ingest.runner.utils import update_download_dir_hash
from unstructured.ingest.runner.writers import writer_map


def discord(
    verbose: bool,
    read_config: ReadConfig,
    partition_config: PartitionConfig,
    channels: t.List[str],
    token: str,
    period: t.Optional[int],
    writer_type: t.Optional[str] = None,
    writer_kwargs: t.Optional[dict] = None,
    **kwargs,
):
    writer_kwargs = writer_kwargs if writer_kwargs else {}

    ingest_log_streaming_init(logging.DEBUG if verbose else logging.INFO)

    hashed_dir_name = hashlib.sha256(
        ",".join(channels).encode("utf-8"),
    )

    read_config.download_dir = update_download_dir_hash(
        connector_name="discord",
        read_config=read_config,
        hashed_dir_name=hashed_dir_name,
        logger=logger,
    )

    from unstructured.ingest.connector.discord import (
        DiscordSourceConnector,
        SimpleDiscordConfig,
    )

    source_doc_connector = DiscordSourceConnector(  # type: ignore
        connector_config=SimpleDiscordConfig(
            channels=channels,
            days=period,
            token=token,
            verbose=verbose,
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
