from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Generator, Optional, TypeVar

from dataclasses_json import DataClassJsonMixin

from unstructured.ingest.v2.interfaces.connector import BaseConnector
from unstructured.ingest.v2.interfaces.file_data import FileData
from unstructured.ingest.v2.interfaces.process import BaseProcess


@dataclass
class IndexerConfig(DataClassJsonMixin):
    pass


config_type = TypeVar("config_type", bound=IndexerConfig)


@dataclass
class Indexer(BaseProcess, BaseConnector, ABC):
    index_config: Optional[config_type] = None

    def is_async(self) -> bool:
        return False

    @abstractmethod
    def run(self, **kwargs) -> Generator[FileData, None, None]:
        pass
