import hashlib
import logging
import typing as t

from unstructured.ingest.logger import ingest_log_streaming_init, logger
from unstructured.ingest.runner.base_runner import Runner
from unstructured.ingest.runner.utils import update_download_dir_hash


class ElasticSearchRunner(Runner):
    def run(
        self,
        url: str,
        index_name: str,
        jq_query: t.Optional[str] = None,
        **kwargs,
    ):
        ingest_log_streaming_init(logging.DEBUG if self.processor_config.verbose else logging.INFO)

        hashed_dir_name = hashlib.sha256(
            f"{url}_{index_name}".encode(
                "utf-8",
            ),
        )

        self.read_config.download_dir = update_download_dir_hash(
            connector_name="elasticsearch",
            read_config=self.read_config,
            hashed_dir_name=hashed_dir_name,
            logger=logger,
        )

        from unstructured.ingest.connector.elasticsearch import (
            ElasticsearchSourceConnector,
            SimpleElasticsearchConfig,
        )

        source_doc_connector = ElasticsearchSourceConnector(  # type: ignore
            connector_config=SimpleElasticsearchConfig(
                url=url,
                index_name=index_name,
                jq_query=jq_query,
            ),
            read_config=self.read_config,
            processor_config=self.processor_config,
        )

        self.process_documents(source_doc_connector=source_doc_connector)
