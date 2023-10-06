import hashlib
import logging
import typing as t

from unstructured.ingest.logger import ingest_log_streaming_init, logger
from unstructured.ingest.runner.base_runner import Runner
from unstructured.ingest.runner.utils import update_download_dir_hash


class OneDriveRunner(Runner):
    def run(
        self,
        tenant: str,
        user_pname: str,
        client_id: str,
        client_cred: str,
        authority_url: t.Optional[str] = None,
        path: t.Optional[str] = None,
        recursive: bool = False,
        **kwargs,
    ):
        ingest_log_streaming_init(logging.DEBUG if self.processor_config.verbose else logging.INFO)

        hashed_dir_name = hashlib.sha256(
            f"{tenant}_{user_pname}".encode("utf-8"),
        )

        self.read_config.download_dir = update_download_dir_hash(
            connector_name="onedrive",
            read_config=self.read_config,
            hashed_dir_name=hashed_dir_name,
            logger=logger,
        )

        from unstructured.ingest.connector.onedrive import (
            OneDriveSourceConnector,
            SimpleOneDriveConfig,
        )

        source_doc_connector = OneDriveSourceConnector(  # type: ignore
            connector_config=SimpleOneDriveConfig(
                client_id=client_id,
                client_credential=client_cred,
                user_pname=user_pname,
                tenant=tenant,
                authority_url=authority_url,
                path=path,
                recursive=recursive,
            ),
            read_config=self.read_config,
            processor_config=self.processor_config,
        )

        self.process_documents(source_doc_connector=source_doc_connector)
