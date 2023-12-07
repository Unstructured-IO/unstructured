import typing as t
from dataclasses import dataclass

from unstructured.ingest.enhanced_dataclass import EnhancedDataClassJsonMixin
from unstructured.ingest.interfaces import BaseDestinationConnector
from unstructured.ingest.runner.writers.base_writer import Writer

if t.TYPE_CHECKING:
    from unstructured.ingest.connector.s3 import S3WriteConfig, SimpleS3Config


@dataclass
class S3Writer(Writer, EnhancedDataClassJsonMixin):
    connector_config: "SimpleS3Config"
    write_config: "S3WriteConfig"

    def get_connector(self, **kwargs) -> BaseDestinationConnector:
        from unstructured.ingest.connector.s3 import (
            S3DestinationConnector,
        )

        return S3DestinationConnector(
            write_config=self.write_config, connector_config=self.connector_config
        )
