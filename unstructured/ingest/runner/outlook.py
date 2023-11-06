import hashlib
import logging
import typing as t

from unstructured.ingest.logger import ingest_log_streaming_init, logger
from unstructured.ingest.runner.base_runner import Runner
from unstructured.ingest.runner.utils import update_download_dir_hash


class OutlookRunner(Runner):
    def run(
        self,
        user_email: str,
        recursive: bool = False,
        client_id: t.Optional[str] = None,
        client_cred: t.Optional[str] = None,
        tenant: t.Optional[str] = None,
        authority_url: t.Optional[str] = None,
        outlook_folders: t.Optional[t.List[str]] = None,
        **kwargs,
    ):
        outlook_folders = outlook_folders if outlook_folders else []
        ingest_log_streaming_init(logging.DEBUG if self.processor_config.verbose else logging.INFO)

        hashed_dir_name = hashlib.sha256(user_email.encode("utf-8"))

        self.read_config.download_dir = update_download_dir_hash(
            connector_name="outlook",
            read_config=self.read_config,
            hashed_dir_name=hashed_dir_name,
            logger=logger,
        )

        from unstructured.ingest.connector.outlook import (
            OutlookSourceConnector,
            SimpleOutlookConfig,
        )

        source_doc_connector = OutlookSourceConnector(  # type: ignore
            connector_config=SimpleOutlookConfig(
                client_id=client_id,
                client_credential=client_cred,
                user_email=user_email,
                tenant=tenant,
                authority_url=authority_url,
                ms_outlook_folders=outlook_folders,
                recursive=recursive,
            ),
            read_config=self.read_config,
            processor_config=self.processor_config,
        )

        self.process_documents(source_doc_connector=source_doc_connector)
