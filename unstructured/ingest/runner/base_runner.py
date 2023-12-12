import logging
import typing as t
from abc import ABC, abstractmethod
from dataclasses import dataclass

from unstructured.ingest.enhanced_dataclass import EnhancedDataClassJsonMixin
from unstructured.ingest.interfaces import (
    BaseConnectorConfig,
    BaseDestinationConnector,
    BaseSourceConnector,
    ChunkingConfig,
    EmbeddingConfig,
    PartitionConfig,
    PermissionsConfig,
    ProcessorConfig,
    ReadConfig,
    RetryStrategyConfig,
)
from unstructured.ingest.logger import ingest_log_streaming_init
from unstructured.ingest.processor import process_documents
from unstructured.ingest.runner.writers.base_writer import Writer


@dataclass
class Runner(EnhancedDataClassJsonMixin, ABC):
    connector_config: BaseConnectorConfig
    processor_config: ProcessorConfig
    read_config: ReadConfig
    partition_config: PartitionConfig
    writer: t.Optional[Writer] = None
    writer_kwargs: t.Optional[dict] = None
    embedding_config: t.Optional[EmbeddingConfig] = None
    chunking_config: t.Optional[ChunkingConfig] = None
    permissions_config: t.Optional[PermissionsConfig] = None
    retry_strategy_config: t.Optional[RetryStrategyConfig] = None

    def run(self, *args, **kwargs):
        ingest_log_streaming_init(logging.DEBUG if self.processor_config.verbose else logging.INFO)
        self.update_read_config()
        source_connector = self.get_source_connector()
        self.process_documents(
            source_doc_connector=source_connector,
        )

    @abstractmethod
    def update_read_config(self):
        pass

    @abstractmethod
    def get_source_connector_cls(self) -> t.Type[BaseSourceConnector]:
        pass

    def get_source_connector(self) -> BaseSourceConnector:
        source_connector_cls = self.get_source_connector_cls()
        return source_connector_cls(
            processor_config=self.processor_config,
            connector_config=self.connector_config,
            read_config=self.read_config,
        )

    def get_dest_doc_connector(self) -> t.Optional[BaseDestinationConnector]:
        writer_kwargs = self.writer_kwargs if self.writer_kwargs else {}
        if self.writer:
            return self.writer.get_connector(**writer_kwargs)
        return None

    def get_permissions_config(self) -> t.Optional[PermissionsConfig]:
        if self.permissions_config is None:
            return None

        permissions_config_filled = bool(
            self.permissions_config.application_id
            and self.permissions_config.client_cred
            and self.permissions_config.tenant,
        )

        return self.permissions_config if permissions_config_filled else None

    def process_documents(self, source_doc_connector: BaseSourceConnector):
        process_documents(
            processor_config=self.processor_config,
            source_doc_connector=source_doc_connector,
            partition_config=self.partition_config,
            dest_doc_connector=self.get_dest_doc_connector(),
            embedder_config=self.embedding_config,
            chunking_config=self.chunking_config,
            permissions_config=self.get_permissions_config(),
            retry_strategy_config=self.retry_strategy_config,
        )
