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
class SimpleGsConfig(SimpleFsspecConfig):
    pass


class GsIngestDoc(FsspecIngestDoc):
    @requires_dependencies(["gcsfs", "fsspec"])
    def get_file(self):
        super().get_file()


@requires_dependencies(["gcsfs", "fsspec"])
class GsConnector(FsspecConnector):
    ingest_doc_cls: Type[GsIngestDoc] = GsIngestDoc

    def __init__(
        self,
        config: SimpleGsConfig,
        standard_config: StandardConnectorConfig,
    ) -> None:
        super().__init__(standard_config, config)
