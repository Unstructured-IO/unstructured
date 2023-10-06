import logging
import typing as t

from unstructured.ingest.logger import ingest_log_streaming_init
from unstructured.ingest.runner.base_runner import Runner


class LocalRunner(Runner):
    def run(
        self,
        input_path: str,
        recursive: bool = False,
        file_glob: t.Optional[str] = None,
        **kwargs,
    ):
        ingest_log_streaming_init(logging.DEBUG if self.processor_config.verbose else logging.INFO)

        from unstructured.ingest.connector.local import (
            LocalSourceConnector,
            SimpleLocalConfig,
        )

        source_doc_connector = LocalSourceConnector(  # type: ignore
            connector_config=SimpleLocalConfig(
                input_path=input_path,
                recursive=recursive,
                file_glob=file_glob,
            ),
            read_config=self.read_config,
            processor_config=self.processor_config,
        )

        self.process_documents(source_doc_connector=source_doc_connector)
