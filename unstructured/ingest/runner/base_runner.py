import typing as t
from abc import ABC, abstractmethod
from dataclasses import dataclass

from unstructured.ingest.interfaces import EmbeddingConfig, PartitionConfig, ReadConfig


@dataclass
class Runner(ABC):
    read_config: ReadConfig
    partition_config: PartitionConfig
    verbose: bool = False
    writer_type: t.Optional[str] = None
    writer_kwargs: t.Optional[dict] = None
    embedding_config: t.Optional[EmbeddingConfig] = None

    @abstractmethod
    def run(self, *args, **kwargs):
        pass
