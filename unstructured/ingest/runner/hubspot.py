import hashlib
import logging
import typing as t

from unstructured.ingest.logger import ingest_log_streaming_init, logger
from unstructured.ingest.runner.base_runner import Runner
from unstructured.ingest.runner.utils import update_download_dir_hash


class HubSpotRunner(Runner):
    def run(
        self,
        api_token: str,
        object_types: t.Optional[t.List[str]] = None,
        custom_properties: t.Optional[t.Dict[str, t.List[str]]] = None,
        **kwargs,
    ):
        ingest_log_streaming_init(logging.DEBUG if self.processor_config.verbose else logging.INFO)

        hashed_dir_name = hashlib.sha256(
            api_token.encode("utf-8"),
        )

        self.read_config.download_dir = update_download_dir_hash(
            connector_name="hubspot",
            read_config=self.read_config,
            hashed_dir_name=hashed_dir_name,
            logger=logger,
        )

        from unstructured.ingest.connector.hubspot import (
            HubSpotSourceConnector,
            SimpleHubSpotConfig,
        )

        source_doc_connector = HubSpotSourceConnector(  # type: ignore
            connector_config=SimpleHubSpotConfig(
                api_token=api_token,
                object_types=object_types,
                custom_properties=custom_properties,
            ),
            read_config=self.read_config,
            processor_config=self.processor_config,
        )

        self.process_documents(
            source_doc_connector=source_doc_connector,
        )
