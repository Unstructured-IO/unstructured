import typing as t
from dataclasses import dataclass

from unstructured.ingest.interfaces import BaseDestinationConnector
from unstructured.ingest.runner.writers.base_writer import Writer

if t.TYPE_CHECKING:
    from unstructured.ingest.connector.kdbai import KDBAIWriteConfig, SimpleKDBAIConfig


@dataclass
class KDBAIWriter(Writer):
    write_config: "KDBAIWriteConfig"
    connector_config: "SimpleKDBAIConfig"

    def get_connector_cls(self) -> t.Type[BaseDestinationConnector]:
        from unstructured.ingest.connector.kdbai import (
            KDBAIDestinationConnector,
        )

        return KDBAIDestinationConnector
