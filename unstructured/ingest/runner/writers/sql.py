import typing as t
from dataclasses import dataclass

from unstructured.ingest.interfaces import BaseDestinationConnector
from unstructured.ingest.runner.writers.base_writer import Writer

if t.TYPE_CHECKING:
    from unstructured.ingest.connector.sql import SimpleSqlConfig
    from unstructured.ingest.interfaces import WriteConfig


@dataclass
class SqlWriter(Writer):
    write_config: "WriteConfig"
    connector_config: "SimpleSqlConfig"

    def get_connector_cls(self) -> t.Type[BaseDestinationConnector]:
        from unstructured.ingest.connector.sql import (
            SqlDestinationConnector,
        )

        return SqlDestinationConnector
