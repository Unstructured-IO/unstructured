from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Generator, Optional, TypeVar

from unstructured.ingest.enhanced_dataclass import EnhancedDataClassJsonMixin
from unstructured.ingest.v2.interfaces.connector import BaseConnector
from unstructured.ingest.v2.interfaces.file_data import FileData
from unstructured.ingest.v2.interfaces.process import BaseProcess


@dataclass
class IndexerConfig(EnhancedDataClassJsonMixin):
    pass


IndexerConfigT = TypeVar("IndexerConfigT", bound=IndexerConfig)


class Indexer(BaseProcess, BaseConnector, ABC):
    connector_type: str
    index_config: Optional[IndexerConfigT] = None

    def is_async(self) -> bool:
        return False

    @abstractmethod
    def run(self, **kwargs: Any) -> Generator[FileData, None, None]:
        pass
