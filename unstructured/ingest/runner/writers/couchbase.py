import typing as t
from dataclasses import dataclass

from unstructured.ingest.interfaces import BaseDestinationConnector
from unstructured.ingest.runner.writers.base_writer import Writer

if t.TYPE_CHECKING:
    from unstructured.ingest.connector.couchbase import CouchbaseWriteConfig, SimpleCouchbaseConfig


@dataclass
class CouchbaseWriter(Writer):
    write_config: "CouchbaseWriteConfig"
    connector_config: "SimpleCouchbaseConfig"

    def get_connector_cls(self) -> t.Type[BaseDestinationConnector]:
        from unstructured.ingest.connector.couchbase import CouchbaseDestinationConnector

        return CouchbaseDestinationConnector
