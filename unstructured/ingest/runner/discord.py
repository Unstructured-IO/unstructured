import hashlib
import logging
import typing as t

from unstructured.ingest.logger import ingest_log_streaming_init, logger
from unstructured.ingest.runner.base_runner import Runner
from unstructured.ingest.runner.utils import update_download_dir_hash


class DiscordRunner(Runner):
    def run(
        self,
        channels: t.List[str],
        token: str,
        period: t.Optional[int] = None,
        **kwargs,
    ):
        ingest_log_streaming_init(logging.DEBUG if self.processor_config.verbose else logging.INFO)

        hashed_dir_name = hashlib.sha256(
            ",".join(channels).encode("utf-8"),
        )

        self.read_config.download_dir = update_download_dir_hash(
            connector_name="discord",
            read_config=self.read_config,
            hashed_dir_name=hashed_dir_name,
            logger=logger,
        )

        from unstructured.ingest.connector.discord import (
            DiscordSourceConnector,
            SimpleDiscordConfig,
        )

        source_doc_connector = DiscordSourceConnector(  # type: ignore
            connector_config=SimpleDiscordConfig(
                channels=channels,
                days=period,
                token=token,
            ),
            read_config=self.read_config,
            processor_config=self.processor_config,
        )

        self.process_documents(source_doc_connector=source_doc_connector)
