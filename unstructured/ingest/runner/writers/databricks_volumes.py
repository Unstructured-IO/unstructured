import typing as t
from dataclasses import dataclass

from unstructured.ingest.enhanced_dataclass import EnhancedDataClassJsonMixin
from unstructured.ingest.interfaces import BaseDestinationConnector
from unstructured.ingest.runner.writers.base_writer import Writer

if t.TYPE_CHECKING:
    from unstructured.ingest.connector.databricks_volumes import (
        DatabricksVolumesWriteConfig,
        SimpleDatabricksVolumesConfig,
    )


@dataclass
class DatabricksVolumesWriter(Writer, EnhancedDataClassJsonMixin):
    write_config: "DatabricksVolumesWriteConfig"
    connector_config: "SimpleDatabricksVolumesConfig"

    def get_connector_cls(self) -> t.Type[BaseDestinationConnector]:
        from unstructured.ingest.connector.databricks_volumes import (
            DatabricksVolumesDestinationConnector,
        )

        return DatabricksVolumesDestinationConnector
