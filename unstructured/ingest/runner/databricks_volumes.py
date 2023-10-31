import hashlib
import logging

from unstructured.ingest.logger import ingest_log_streaming_init, logger
from unstructured.ingest.runner.base_runner import Runner
from unstructured.ingest.runner.utils import update_download_dir_hash


class DatabricksVolumesRunner(Runner):
    def run(
        self,
        auth_configs: dict,
        remote_url: str,
        recursive: bool = False,
        **kwargs,
    ):
        ingest_log_streaming_init(logging.DEBUG if self.processor_config.verbose else logging.INFO)

        hashed_dir_name = hashlib.sha256(
            remote_url.encode("utf-8"),
        )

        self.read_config.download_dir = update_download_dir_hash(
            connector_name="airtable",
            read_config=self.read_config,
            hashed_dir_name=hashed_dir_name,
            logger=logger,
        )

        print(f"auth configs: {auth_configs}")
        print(f"remote_url: {remote_url}")
        return

        from unstructured.ingest.connector.databricks_volumes import (
            DatabricksVolumesSourceConnector,
            SimpleDatabricksVolumesConfig,
        )

        source_doc_connector = DatabricksVolumesSourceConnector(  # type: ignore
            processor_config=self.processor_config,
            connector_config=SimpleDatabricksVolumesConfig(
                auth_configs=auth_configs,
                remote_url=remote_url,
                recursive=recursive,
            ),
            read_config=self.read_config,
        )

        self.process_documents(
            source_doc_connector=source_doc_connector,
        )
