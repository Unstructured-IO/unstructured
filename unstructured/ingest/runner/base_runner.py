import typing as t
from abc import ABC, abstractmethod
from dataclasses import dataclass

from unstructured.ingest.interfaces import (
    BaseDestinationConnector,
    BaseSourceConnector,
    ChunkingConfig,
    EmbeddingConfig,
    FsspecConfig,
    PartitionConfig,
    PermissionsConfig,
    ProcessorConfig,
    ReadConfig,
    RetryStrategyConfig,
)
from unstructured.ingest.processor import process_documents
from unstructured.ingest.runner.writers import writer_map


@dataclass
class Runner(ABC):
    processor_config: ProcessorConfig
    read_config: ReadConfig
    partition_config: PartitionConfig
    writer_type: t.Optional[str] = None
    writer_kwargs: t.Optional[dict] = None
    embedding_config: t.Optional[EmbeddingConfig] = None
    chunking_config: t.Optional[ChunkingConfig] = None
    permissions_config: t.Optional[PermissionsConfig] = None
    retry_strategy_config: t.Optional[RetryStrategyConfig] = None

    @abstractmethod
    def run(self, *args, **kwargs):
        pass

    def get_dest_doc_connector(self) -> t.Optional[BaseDestinationConnector]:
        writer_kwargs = self.writer_kwargs if self.writer_kwargs else {}
        if self.writer_type:
            writer = writer_map[self.writer_type]
            return writer(**writer_kwargs)
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


@dataclass
class FsspecBaseRunner(Runner):
    # TODO make this field required when python3.8 no longer supported
    # python3.8 dataclass doesn't support default values in child classes, but this
    # fsspec_config should be required in this class.
    fsspec_config: t.Optional[FsspecConfig] = None

    def __post_init__(self):
        if self.fsspec_config is None:
            raise ValueError("fsspec_config must exist")
