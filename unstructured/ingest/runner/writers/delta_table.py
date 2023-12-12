import typing as t
from dataclasses import dataclass

from unstructured.ingest.interfaces import BaseDestinationConnector
from unstructured.ingest.runner.writers.base_writer import Writer

if t.TYPE_CHECKING:
    from unstructured.ingest.connector.delta_table import (
        DeltaTableWriteConfig,
        SimpleDeltaTableConfig,
    )


@dataclass
class DeltaTableWriter(Writer):
    write_config: "DeltaTableWriteConfig"
    connector_config: "SimpleDeltaTableConfig"

    def get_connector_cls(self) -> t.Type[BaseDestinationConnector]:
        from unstructured.ingest.connector.delta_table import (
            DeltaTableDestinationConnector,
        )

        return DeltaTableDestinationConnector
