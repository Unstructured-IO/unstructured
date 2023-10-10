import hashlib
import logging
import typing as t

from unstructured.ingest.logger import ingest_log_streaming_init, logger
from unstructured.ingest.runner.base_runner import Runner
from unstructured.ingest.runner.utils import update_download_dir_hash


class SlackRunner(Runner):
    def run(
        self,
        channels: t.List[str],
        token: str,
        start_date: t.Optional[str] = None,
        end_date: t.Optional[str] = None,
        **kwargs,
    ):
        ingest_log_streaming_init(logging.DEBUG if self.processor_config.verbose else logging.INFO)

        hashed_dir_name = hashlib.sha256(
            ",".join(channels).encode("utf-8"),
        )

        self.read_config.download_dir = update_download_dir_hash(
            connector_name="slack",
            read_config=self.read_config,
            hashed_dir_name=hashed_dir_name,
            logger=logger,
        )

        from unstructured.ingest.connector.slack import (
            SimpleSlackConfig,
            SlackSourceConnector,
        )

        source_doc_connector = SlackSourceConnector(  # type: ignore
            connector_config=SimpleSlackConfig(
                channels=channels,
                token=token,
                oldest=start_date,
                latest=end_date,
            ),
            read_config=self.read_config,
            processor_config=self.processor_config,
        )

        self.process_documents(source_doc_connector=source_doc_connector)
