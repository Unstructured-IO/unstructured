import hashlib
import logging
import typing as t
from uuid import UUID

from unstructured.ingest.logger import ingest_log_streaming_init, logger
from unstructured.ingest.runner.base_runner import Runner
from unstructured.ingest.runner.utils import update_download_dir_hash


class NotionRunner(Runner):
    def run(
        self,
        notion_api_key: str,
        recursive: bool = False,
        max_retries: t.Optional[int] = None,
        max_time: t.Optional[float] = None,
        page_ids: t.Optional[t.List[str]] = None,
        database_ids: t.Optional[t.List[str]] = None,
        **kwargs,
    ):
        page_ids = [str(UUID(p.strip())) for p in page_ids] if page_ids else []
        database_ids = [str(UUID(d.strip())) for d in database_ids] if database_ids else []

        ingest_log_streaming_init(logging.DEBUG if self.processor_config.verbose else logging.INFO)
        if not page_ids and not database_ids:
            raise ValueError("no page ids nor database ids provided")

        if page_ids and database_ids:
            hashed_dir_name = hashlib.sha256(
                "{},{}".format(",".join(page_ids), ",".join(database_ids)).encode("utf-8"),
            )
        elif page_ids:
            hashed_dir_name = hashlib.sha256(
                ",".join(page_ids).encode("utf-8"),
            )
        elif database_ids:
            hashed_dir_name = hashlib.sha256(
                ",".join(database_ids).encode("utf-8"),
            )
        else:
            raise ValueError("could not create local cache directory name")

        self.read_config.download_dir = update_download_dir_hash(
            connector_name="notion",
            read_config=self.read_config,
            hashed_dir_name=hashed_dir_name,
            logger=logger,
        )

        from unstructured.ingest.connector.notion.connector import (
            NotionSourceConnector,
            SimpleNotionConfig,
        )

        source_doc_connector = NotionSourceConnector(  # type: ignore
            connector_config=SimpleNotionConfig(
                page_ids=page_ids,
                database_ids=database_ids,
                notion_api_key=notion_api_key,
                recursive=recursive,
            ),
            read_config=self.read_config,
            processor_config=self.processor_config,
            retry_strategy_config=self.retry_strategy_config,
        )

        self.process_documents(source_doc_connector=source_doc_connector)
