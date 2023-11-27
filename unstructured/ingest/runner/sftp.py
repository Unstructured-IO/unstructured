import logging
import typing as t

from unstructured.ingest.logger import ingest_log_streaming_init, logger
from unstructured.ingest.runner.base_runner import FsspecBaseRunner
from unstructured.ingest.runner.utils import update_download_dir_remote_url


class SftpRunner(FsspecBaseRunner):
    def run(
        self,
        username: str = None,
        password: str = None,
        **kwargs,
    ):
        ingest_log_streaming_init(logging.DEBUG if self.processor_config.verbose else logging.INFO)

        self.read_config.download_dir = update_download_dir_remote_url(
            connector_name="sftp",
            read_config=self.read_config,
            remote_url=self.fsspec_config.remote_url,  # type: ignore
            logger=logger,
        )

        from unstructured.ingest.connector.sftp import SftpSourceConnector, SimpleSftpConfig

        connector_config = SimpleSftpConfig.from_dict(self.fsspec_config.to_dict())  # type: ignore
        connector_config.access_kwargs = {"host": connector_config.host, "port": connector_config.port, "username": username, "password": password}
        source_doc_connector = SftpSourceConnector(  # type: ignore
            read_config=self.read_config,
            connector_config=connector_config,
            processor_config=self.processor_config,
        )

        self.process_documents(source_doc_connector=source_doc_connector)
