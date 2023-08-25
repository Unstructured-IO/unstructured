import hashlib
import logging
from typing import List, Optional

from unstructured.ingest.interfaces import (
    ReadConfigs,
)
from unstructured.ingest.logger import ingest_log_streaming_init, logger
from unstructured.ingest.runner.utils2 import update_download_dir_hash


def read(
    verbose: bool,
    read_configs: ReadConfigs,
    api_key: str,
    recursive: bool,
    page_ids: Optional[List[str]] = None,
    database_ids: Optional[List[str]] = None,
    **kwargs,
):
    ingest_log_streaming_init(logging.DEBUG if verbose else logging.INFO)
    if not page_ids and not database_ids:
        raise ValueError("no page ids nor database ids provided")

    if page_ids and database_ids:
        hashed_dir_name = hashlib.sha256(
            f"{page_ids},{database_ids}".encode("utf-8"),
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
    read_configs.download_dir = update_download_dir_hash(
        connector_name="notion_pkg",
        read_config=read_configs,
        hashed_dir_name=hashed_dir_name,
        logger=logger,
    )
    # TODO refactor to only download content

    # from unstructured.ingest.connector.notion_pkg.connector import (
    #     NotionConnector,
    #     SimpleNotionConfig,
    # )

    # doc_connector = NotionConnector(  # type: ignore
    #     standard_config=connector_config,
    #     config=SimpleNotionConfig(
    #         page_ids=page_ids if page_ids else [],
    #         database_ids=database_ids if database_ids else [],
    #         api_key=api_key,
    #         verbose=verbose,
    #         recursive=recursive,
    #         logger=logger,
    #     ),
    # )

    # process_documents(doc_connector=doc_connector, processor_config=processor_config)
