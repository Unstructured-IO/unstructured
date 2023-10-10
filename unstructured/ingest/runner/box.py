import logging
import typing as t

from unstructured.ingest.logger import ingest_log_streaming_init, logger
from unstructured.ingest.runner.base_runner import Runner
from unstructured.ingest.runner.utils import update_download_dir_remote_url


class BoxRunner(Runner):
    def run(
        self,
        remote_url: str,
        recursive: bool = False,
        box_app_config: t.Optional[str] = None,
        **kwargs,
    ):
        ingest_log_streaming_init(logging.DEBUG if self.processor_config.verbose else logging.INFO)

        self.read_config.download_dir = update_download_dir_remote_url(
            connector_name="box",
            read_config=self.read_config,
            remote_url=remote_url,
            logger=logger,
        )

        from unstructured.ingest.connector.box import BoxSourceConnector, SimpleBoxConfig

        source_doc_connector = BoxSourceConnector(  # type: ignore
            read_config=self.read_config,
            connector_config=SimpleBoxConfig(
                path=remote_url,
                recursive=recursive,
                access_kwargs={"box_app_config": box_app_config},
            ),
            processor_config=self.processor_config,
        )

        self.process_documents(source_doc_connector=source_doc_connector)
