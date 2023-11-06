import hashlib
import logging
import typing as t

from unstructured.ingest.logger import ingest_log_streaming_init, logger
from unstructured.ingest.runner.base_runner import Runner
from unstructured.ingest.runner.utils import update_download_dir_hash


class BiomedRunner(Runner):
    def run(
        self,
        max_request_time: int = 45,
        path: t.Optional[str] = None,
        api_id: t.Optional[str] = None,
        api_from: t.Optional[str] = None,
        api_until: t.Optional[str] = None,
        **kwargs,
    ):
        ingest_log_streaming_init(logging.DEBUG if self.processor_config.verbose else logging.INFO)
        base_path = (
            path
            if path
            else "{}-{}-{}".format(
                api_id if api_id else "",
                api_from if api_from else "",
                api_until if api_until else "",
            )
        )

        hashed_dir_name = hashlib.sha256(
            base_path.encode("utf-8"),
        )

        self.read_config.download_dir = update_download_dir_hash(
            connector_name="biomed",
            read_config=self.read_config,
            hashed_dir_name=hashed_dir_name,
            logger=logger,
        )

        from unstructured.ingest.connector.biomed import (
            BiomedSourceConnector,
            SimpleBiomedConfig,
        )

        source_doc_connector = BiomedSourceConnector(  # type: ignore
            processor_config=self.processor_config,
            connector_config=SimpleBiomedConfig(
                path=path,
                id_=api_id,
                from_=api_from,
                until=api_until,
                request_timeout=max_request_time,
            ),
            read_config=self.read_config,
        )

        self.process_documents(source_doc_connector=source_doc_connector)
