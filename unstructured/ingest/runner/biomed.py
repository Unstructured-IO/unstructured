import hashlib
import logging
import typing as t

from unstructured.ingest.logger import ingest_log_streaming_init, logger
from unstructured.ingest.runner.base_runner import Runner
from unstructured.ingest.runner.utils import update_download_dir_hash

if t.TYPE_CHECKING:
    from unstructured.ingest.connector.biomed import SimpleBiomedConfig


class BiomedRunner(Runner):
    connector_config: "SimpleBiomedConfig"

    def run(
        self,
        **kwargs,
    ):
        ingest_log_streaming_init(logging.DEBUG if self.processor_config.verbose else logging.INFO)
        base_path = (
            self.connector_config.path
            if self.connector_config.path
            else "{}-{}-{}".format(
                self.connector_config.api_id if self.connector_config.api_id else "",
                self.connector_config.api_from if self.connector_config.api_from else "",
                self.connector_config.api_until if self.connector_config.api_until else "",
            )
        )

        hashed_dir_name = hashlib.sha256(
            base_path.encode("utf-8"),
        )

        self.read_config.download_dir = update_download_dir_hash(
            connector_name="biomed",
            read_config=self.read_config,
            hashed_dir_name=hashed_dir_name,
            logger=logger,
        )

        from unstructured.ingest.connector.biomed import (
            BiomedSourceConnector,
        )

        source_doc_connector = BiomedSourceConnector(  # type: ignore
            processor_config=self.processor_config,
            connector_config=self.connector_config,
            read_config=self.read_config,
        )

        self.process_documents(source_doc_connector=source_doc_connector)
