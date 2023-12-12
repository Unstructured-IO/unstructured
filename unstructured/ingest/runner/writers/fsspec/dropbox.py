import typing as t
from dataclasses import dataclass

from unstructured.ingest.interfaces import BaseDestinationConnector
from unstructured.ingest.runner.writers.base_writer import Writer

if t.TYPE_CHECKING:
    from unstructured.ingest.connector.fsspec.dropbox import DropboxWriteConfig, SimpleDropboxConfig


@dataclass
class DropboxWriter(Writer):
    connector_config: "SimpleDropboxConfig"
    write_config: "DropboxWriteConfig"

    def get_connector_cls(self) -> t.Type[BaseDestinationConnector]:
        from unstructured.ingest.connector.fsspec.dropbox import (
            DropboxDestinationConnector,
        )

        return DropboxDestinationConnector
