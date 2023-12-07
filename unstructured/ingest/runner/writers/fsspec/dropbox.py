import typing as t
from dataclasses import dataclass

from unstructured.ingest.enhanced_dataclass import EnhancedDataClassJsonMixin
from unstructured.ingest.interfaces import BaseDestinationConnector
from unstructured.ingest.runner.writers.base_writer import Writer

if t.TYPE_CHECKING:
    from unstructured.ingest.connector.dropbox import DropboxWriteConfig, SimpleDropboxConfig


@dataclass
class DropboxWriter(Writer, EnhancedDataClassJsonMixin):
    connector_config: "SimpleDropboxConfig"
    write_config: "DropboxWriteConfig"

    def get_connector(self, **kwargs) -> BaseDestinationConnector:
        from unstructured.ingest.connector.fsspec.dropbox import (
            DropboxDestinationConnector,
        )

        return DropboxDestinationConnector(
            write_config=self.write_config,
            connector_config=self.connector_config,
        )
