import hashlib
import logging

from unstructured.ingest.logger import ingest_log_streaming_init, logger
from unstructured.ingest.runner.base_runner import Runner
from unstructured.ingest.runner.utils import update_download_dir_hash


class SharePointRunner(Runner):
    def run(
        self,
        site: str,
        client_id: str,
        client_cred: str,
        path: str,
        files_only: bool = False,
        recursive: bool = False,
        **kwargs,
    ):
        ingest_log_streaming_init(logging.DEBUG if self.processor_config.verbose else logging.INFO)

        hashed_dir_name = hashlib.sha256(
            f"{site}_{path}".encode("utf-8"),
        )

        self.read_config.download_dir = update_download_dir_hash(
            connector_name="sharepoint",
            read_config=self.read_config,
            hashed_dir_name=hashed_dir_name,
            logger=logger,
        )

        from unstructured.ingest.connector.sharepoint import (
            SharepointSourceConnector,
            SimpleSharepointConfig,
        )

        source_doc_connector = SharepointSourceConnector(  # type: ignore
            processor_config=self.processor_config,
            connector_config=SimpleSharepointConfig(
                client_id=client_id,
                client_credential=client_cred,
                site_url=site,
                path=path,
                process_pages=(not files_only),
                recursive=recursive,
            ),
            read_config=self.read_config,
        )

        self.process_documents(
            source_doc_connector=source_doc_connector,
        )
