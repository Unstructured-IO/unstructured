import logging
import typing as t

from unstructured.ingest.logger import ingest_log_streaming_init, logger
from unstructured.ingest.runner.base_runner import Runner
from unstructured.ingest.runner.utils import update_download_dir_remote_url


class S3Runner(Runner):
    def run(
        self,
        remote_url: str,
        recursive: bool = False,
        anonymous: bool = False,
        endpoint_url: t.Optional[str] = None,
        **kwargs,
    ):
        ingest_log_streaming_init(logging.DEBUG if self.processor_config.verbose else logging.INFO)

        self.read_config.download_dir = update_download_dir_remote_url(
            connector_name="s3",
            read_config=self.read_config,
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
            read_config=self.read_config,
            processor_config=self.processor_config,
        )

        self.process_documents(
            source_doc_connector=source_doc_connector,
        )
