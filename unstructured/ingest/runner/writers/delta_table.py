import typing as t
from dataclasses import dataclass

from unstructured.ingest.enhanced_dataclass import EnhancedDataClassJsonMixin
from unstructured.ingest.interfaces import BaseDestinationConnector
from unstructured.ingest.runner.writers.base_writer import Writer

if t.TYPE_CHECKING:
    from unstructured.ingest.connector.delta_table import (
        DeltaTableWriteConfig,
        SimpleDeltaTableConfig,
    )


@dataclass
class DeltaTableWriter(Writer, EnhancedDataClassJsonMixin):
    write_config: t.Optional["DeltaTableWriteConfig"] = None
    connector_config: t.Optional["SimpleDeltaTableConfig"] = None

    def get_connector(self, **kwargs) -> BaseDestinationConnector:
        from unstructured.ingest.connector.delta_table import (
            DeltaTableDestinationConnector,
        )

        return DeltaTableDestinationConnector(
            write_config=self.write_config,
            connector_config=self.connector_config,
        )
