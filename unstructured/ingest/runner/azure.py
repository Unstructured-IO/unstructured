import logging
import typing as t

from unstructured.ingest.logger import ingest_log_streaming_init, logger
from unstructured.ingest.runner.base_runner import FsspecBaseRunner
from unstructured.ingest.runner.utils import update_download_dir_remote_url


class AzureRunner(FsspecBaseRunner):
    def run(
        self,
        account_name: t.Optional[str] = None,
        account_key: t.Optional[str] = None,
        connection_string: t.Optional[str] = None,
        recursive: bool = False,
        **kwargs,
    ):
        ingest_log_streaming_init(logging.DEBUG if self.processor_config.verbose else logging.INFO)

        if not account_name and not connection_string:
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
            SimpleAzureBlobStorageConfig,
        )

        if account_name:
            access_kwargs = {
                "account_name": account_name,
                "account_key": account_key,
            }
        elif connection_string:
            access_kwargs = {"connection_string": connection_string}
        else:
            access_kwargs = {}
        connector_config = SimpleAzureBlobStorageConfig.from_dict(
            self.fsspec_config.to_dict(),  # type: ignore
        )
        connector_config.access_kwargs = access_kwargs
        source_doc_connector = AzureBlobStorageSourceConnector(  # type: ignore
            processor_config=self.processor_config,
            connector_config=connector_config,
            read_config=self.read_config,
        )

        self.process_documents(
            source_doc_connector=source_doc_connector,
        )
