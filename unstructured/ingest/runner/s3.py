import logging

from unstructured.ingest.interfaces import ProcessorConfigs, StandardConnectorConfig
from unstructured.ingest.logger import ingest_log_streaming_init, logger
from unstructured.ingest.processor import process_documents
from unstructured.ingest.runner.utils import update_download_dir_remote_url


def s3(
    verbose: bool,
    connector_config: StandardConnectorConfig,
    processor_config: ProcessorConfigs,
    remote_url: str,
    recursive: bool,
    anonymous: bool,
    **kwargs,
):
    ingest_log_streaming_init(logging.DEBUG if verbose else logging.INFO)

    connector_config.download_dir = update_download_dir_remote_url(
        connector_config=connector_config,
        remote_url=remote_url,
        logger=logger,
    )

    from unstructured.ingest.connector.s3 import S3Connector, SimpleS3Config

    doc_connector = S3Connector(  # type: ignore
        standard_config=connector_config,
        config=SimpleS3Config(
            path=remote_url,
            recursive=recursive,
            access_kwargs={"anon": anonymous},
        ),
    )

    process_documents(doc_connector=doc_connector, processor_config=processor_config)
