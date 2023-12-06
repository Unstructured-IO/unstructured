import logging
import typing as t
from dataclasses import dataclass

from unstructured.ingest.logger import ingest_log_streaming_init, logger
from unstructured.ingest.runner.base_runner import FsspecBaseRunner
from unstructured.ingest.runner.utils import update_download_dir_remote_url

if t.TYPE_CHECKING:
    from unstructured.ingest.connector.s3 import SimpleS3Config


@dataclass
class S3Runner(FsspecBaseRunner):
    fsspec_config: t.Optional["SimpleS3Config"] = None

    def run(
        self,
        **kwargs,
    ):
        ingest_log_streaming_init(logging.DEBUG if self.processor_config.verbose else logging.INFO)

        self.read_config.download_dir = update_download_dir_remote_url(
            connector_name="s3",
            read_config=self.read_config,
            remote_url=self.fsspec_config.remote_url,  # type: ignore
            logger=logger,
        )

        from unstructured.ingest.connector.s3 import S3SourceConnector

        source_doc_connector = S3SourceConnector(  # type: ignore
            connector_config=self.fsspec_config,
            read_config=self.read_config,
            processor_config=self.processor_config,
        )

        self.process_documents(
            source_doc_connector=source_doc_connector,
        )
