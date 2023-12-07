import logging
import typing as t

from unstructured.ingest.logger import ingest_log_streaming_init, logger
from unstructured.ingest.runner.base_runner import Runner
from unstructured.ingest.runner.utils import update_download_dir_remote_url

if t.TYPE_CHECKING:
    from unstructured.ingest.connector.fsspec.box import SimpleBoxConfig


class BoxRunner(Runner):
    connector_config: t.Optional["SimpleBoxConfig"] = None

    def run(
        self,
        **kwargs,
    ):
        ingest_log_streaming_init(logging.DEBUG if self.processor_config.verbose else logging.INFO)

        self.read_config.download_dir = update_download_dir_remote_url(
            connector_name="box",
            read_config=self.read_config,
            remote_url=self.connector_config.remote_url,  # type: ignore
            logger=logger,
        )

        from unstructured.ingest.connector.fsspec.box import BoxSourceConnector

        source_doc_connector = BoxSourceConnector(  # type: ignore
            read_config=self.read_config,
            connector_config=self.connector_config,
            processor_config=self.processor_config,
        )

        self.process_documents(source_doc_connector=source_doc_connector)
