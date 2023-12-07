import typing as t
from dataclasses import dataclass

from unstructured.ingest.enhanced_dataclass import EnhancedDataClassJsonMixin
from unstructured.ingest.interfaces import BaseDestinationConnector
from unstructured.ingest.runner.writers.base_writer import Writer

if t.TYPE_CHECKING:
    from unstructured.ingest.connector.gcs import GcsWriteConfig, SimpleGcsConfig


@dataclass
class GcsWriter(Writer, EnhancedDataClassJsonMixin):
    connector_config: "SimpleGcsConfig"
    write_config: "GcsWriteConfig"

    def get_connector(self, **kwargs) -> BaseDestinationConnector:
        from unstructured.ingest.connector.fsspec.gcs import GcsDestinationConnector

        return GcsDestinationConnector(
            write_config=self.write_config, connector_config=self.connector_config
        )
