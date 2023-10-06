import logging
import warnings
from urllib.parse import urlparse

from unstructured.ingest.logger import ingest_log_streaming_init, logger
from unstructured.ingest.runner.base_runner import Runner
from unstructured.ingest.runner.utils import update_download_dir_remote_url


class FsspecRunner(Runner):
    def run(
        self,
        remote_url: str,
        recursive: bool = False,
        **kwargs,
    ):
        ingest_log_streaming_init(logging.DEBUG if self.processor_config.verbose else logging.INFO)

        self.read_config.download_dir = update_download_dir_remote_url(
            connector_name="fsspec",
            read_config=self.read_config,
            remote_url=remote_url,
            logger=logger,
        )

        protocol = urlparse(remote_url).scheme
        warnings.warn(
            f"`fsspec` protocol {protocol} is not directly supported by `unstructured`,"
            " so use it at your own risk. Supported protocols are `gcs`, `gs`, `s3`, `s3a`,"
            "`dropbox`, `abfs` and `az`.",
            UserWarning,
        )

        from unstructured.ingest.connector.fsspec import (
            FsspecSourceConnector,
            SimpleFsspecConfig,
        )

        source_doc_connector = FsspecSourceConnector(  # type: ignore
            connector_config=SimpleFsspecConfig(
                path=remote_url,
                recursive=recursive,
            ),
            read_config=self.read_config,
            processor_config=self.processor_config,
        )

        self.process_documents(source_doc_connector=source_doc_connector)
