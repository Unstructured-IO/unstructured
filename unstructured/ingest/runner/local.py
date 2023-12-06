import logging
import typing as t

from unstructured.ingest.logger import ingest_log_streaming_init
from unstructured.ingest.runner.base_runner import Runner

if t.TYPE_CHECKING:
    from unstructured.ingest.connector.local import SimpleLocalConfig


class LocalRunner(Runner):
    connector_config: "SimpleLocalConfig"

    def run(
        self,
        **kwargs,
    ):
        ingest_log_streaming_init(logging.DEBUG if self.processor_config.verbose else logging.INFO)

        from unstructured.ingest.connector.local import (
            LocalSourceConnector,
        )

        source_doc_connector = LocalSourceConnector(  # type: ignore
            connector_config=self.connector_config,
            read_config=self.read_config,
            processor_config=self.processor_config,
        )

        self.process_documents(source_doc_connector=source_doc_connector)
