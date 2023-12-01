import typing as t
from dataclasses import dataclass

from unstructured.ingest.enhanced_dataclass import EnhancedDataClassJsonMixin
from unstructured.ingest.interfaces import BaseDestinationConnector
from unstructured.ingest.runner.writers.base_writer import Writer

if t.TYPE_CHECKING:
    from unstructured.ingest.connector.box import BoxWriteConfig, SimpleBoxConfig


@dataclass
class BoxWriter(Writer, EnhancedDataClassJsonMixin):
    fsspec_config: t.Optional["SimpleBoxConfig"] = None
    write_config: t.Optional["BoxWriteConfig"] = None

    def get_connector(self, **kwargs) -> BaseDestinationConnector:
        from unstructured.ingest.connector.box import (
            BoxDestinationConnector,
        )

        return BoxDestinationConnector(
            write_config=self.write_config,
            connector_config=self.write_config,
        )
