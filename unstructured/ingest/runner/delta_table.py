import hashlib
import logging
import typing as t
from pathlib import Path

from unstructured.ingest.logger import ingest_log_streaming_init, logger
from unstructured.ingest.runner.base_runner import Runner
from unstructured.ingest.runner.utils import update_download_dir_hash


class DeltaTableRunner(Runner):
    def run(
        self,
        table_uri: t.Union[str, Path],
        version: t.Optional[int] = None,
        storage_options: t.Optional[str] = None,
        without_files: bool = False,
        columns: t.Optional[t.List[str]] = None,
        **kwargs,
    ):
        ingest_log_streaming_init(logging.DEBUG if self.processor_config.verbose else logging.INFO)

        hashed_dir_name = hashlib.sha256(
            str(table_uri).encode("utf-8"),
        )
        self.read_config.download_dir = update_download_dir_hash(
            connector_name="delta_table",
            read_config=self.read_config,
            hashed_dir_name=hashed_dir_name,
            logger=logger,
        )

        from unstructured.ingest.connector.delta_table import (
            DeltaTableSourceConnector,
            SimpleDeltaTableConfig,
        )

        source_doc_connector = DeltaTableSourceConnector(
            connector_config=SimpleDeltaTableConfig(
                table_uri=table_uri,
                version=version,
                storage_options=SimpleDeltaTableConfig.storage_options_from_str(storage_options)
                if storage_options
                else None,
                without_files=without_files,
                columns=columns,
            ),
            read_config=self.read_config,
            processor_config=self.processor_config,
        )

        self.process_documents(source_doc_connector=source_doc_connector)
