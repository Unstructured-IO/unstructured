import logging
import typing as t
from dataclasses import dataclass

from unstructured.ingest.logger import ingest_log_streaming_init, logger
from unstructured.ingest.runner.base_runner import FsspecBaseRunner
from unstructured.ingest.runner.utils import update_download_dir_remote_url

if t.TYPE_CHECKING:
    from unstructured.ingest.connector.azure import SimpleAzureBlobStorageConfig


@dataclass
class AzureRunner(FsspecBaseRunner):
    fsspec_config: t.Optional["SimpleAzureBlobStorageConfig"] = None

    def run(
        self,
        **kwargs,
    ):
        ingest_log_streaming_init(logging.DEBUG if self.processor_config.verbose else logging.INFO)

        if (
            not self.fsspec_config.access_config.account_name
            and not self.fsspec_config.access_config.connection_string
        ):
            raise ValueError(
                "missing either account-name or connection-string",
            )

        self.read_config.download_dir = update_download_dir_remote_url(
            connector_name="azure",
            read_config=self.read_config,
            remote_url=self.fsspec_config.remote_url,  # type: ignore
            logger=logger,
        )

        from unstructured.ingest.connector.azure import (
            AzureBlobStorageSourceConnector,
        )

        source_doc_connector = AzureBlobStorageSourceConnector(  # type: ignore
            processor_config=self.processor_config,
            connector_config=self.fsspec_config,
            read_config=self.read_config,
        )

        self.process_documents(
            source_doc_connector=source_doc_connector,
        )
