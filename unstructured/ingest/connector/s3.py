from dataclasses import dataclass
from typing import Type

from unstructured.ingest.connector.fsspec import (
    FsspecConnector,
    FsspecIngestDoc,
    SimpleFsspecConfig,
)
from unstructured.ingest.interfaces import StandardConnectorConfig


@dataclass
class SimpleS3Config(SimpleFsspecConfig):
    pass


class S3IngestDoc(FsspecIngestDoc):
    def get_file(self):
        super().get_file()


class S3Connector(FsspecConnector):
    ingest_doc_cls: Type[S3IngestDoc] = S3IngestDoc

    def __init__(
        self,
        config: SimpleS3Config,
        standard_config: StandardConnectorConfig,
    ) -> None:
        super().__init__(standard_config, config)
