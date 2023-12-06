from abc import ABC, abstractmethod

from unstructured.ingest.interfaces import BaseDestinationConnector


class Writer(ABC):
    @abstractmethod
    def get_connector(self, **kwargs) -> BaseDestinationConnector:
        pass
