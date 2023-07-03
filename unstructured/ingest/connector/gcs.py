from dataclasses import dataclass
from typing import Type

from unstructured.ingest.connector.fsspec import (
    FsspecConnector,
    FsspecIngestDoc,
    SimpleFsspecConfig,
)
from unstructured.ingest.interfaces import StandardConnectorConfig
from unstructured.utils import requires_dependencies


@dataclass
class SimpleGcsConfig(SimpleFsspecConfig):
    pass


class GcsIngestDoc(FsspecIngestDoc):
    @requires_dependencies(["gcsfs", "fsspec"], extras="gcs")
    def get_file(self):
        super().get_file()


@requires_dependencies(["gcsfs", "fsspec"], extras="gcs")
class GcsConnector(FsspecConnector):
    ingest_doc_cls: Type[GcsIngestDoc] = GcsIngestDoc

    def __init__(
        self,
        config: SimpleGcsConfig,
        standard_config: StandardConnectorConfig,
    ) -> None:
        super().__init__(standard_config, config)
