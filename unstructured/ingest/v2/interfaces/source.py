from abc import ABC
from dataclasses import dataclass
from typing import TypeVar

from unstructured.ingest.v2.interfaces.connector import BaseConnector
from unstructured.ingest.v2.interfaces.downloader import Downloader
from unstructured.ingest.v2.interfaces.indexer import Indexer

indexer_type = TypeVar("indexer_type", bound=Indexer)
downloader_type = TypeVar("downloader_type", bound=Downloader)


@dataclass(kw_only=True)
class Source(BaseConnector, ABC):
    connector_type: str
    indexer: indexer_type
    downloader: downloader_type
