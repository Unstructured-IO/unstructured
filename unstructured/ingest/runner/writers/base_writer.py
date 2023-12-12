import typing as t
from abc import ABC, abstractmethod
from dataclasses import dataclass

from unstructured.ingest.interfaces import (
    BaseConnectorConfig,
    BaseDestinationConnector,
    WriteConfig,
)


@dataclass
class Writer(ABC):
    connector_config: BaseConnectorConfig
    write_config: WriteConfig

    @abstractmethod
    def get_connector_cls(self) -> t.Type[BaseDestinationConnector]:
        pass

    def get_connector(self, **kwargs) -> BaseDestinationConnector:
        connector_cls = self.get_connector_cls()
        return connector_cls(
            write_config=self.write_config,
            connector_config=self.connector_config,
        )
