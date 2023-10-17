import hashlib
import logging
import typing as t

from unstructured.ingest.logger import ingest_log_streaming_init, logger
from unstructured.ingest.runner.base_runner import Runner
from unstructured.ingest.runner.utils import update_download_dir_hash


class ConfluenceRunner(Runner):
    def run(
        self,
        url: str,
        user_email: str,
        api_token: str,
        max_num_of_spaces: int = 500,
        max_num_of_docs_from_each_space: int = 100,
        spaces: t.Optional[t.List[str]] = None,
        **kwargs,
    ):
        spaces = spaces if spaces else []

        ingest_log_streaming_init(logging.DEBUG if self.processor_config.verbose else logging.INFO)

        hashed_dir_name = hashlib.sha256(
            url.encode("utf-8"),
        )

        self.read_config.download_dir = update_download_dir_hash(
            connector_name="confluence",
            read_config=self.read_config,
            hashed_dir_name=hashed_dir_name,
            logger=logger,
        )

        from unstructured.ingest.connector.confluence import (
            ConfluenceSourceConnector,
            SimpleConfluenceConfig,
        )

        source_doc_connector = ConfluenceSourceConnector(  # type: ignore
            processor_config=self.processor_config,
            connector_config=SimpleConfluenceConfig(
                url=url,
                user_email=user_email,
                api_token=api_token,
                spaces=spaces,
                max_number_of_spaces=max_num_of_spaces,
                max_number_of_docs_from_each_space=max_num_of_docs_from_each_space,
            ),
            read_config=self.read_config,
        )

        self.process_documents(source_doc_connector=source_doc_connector)
