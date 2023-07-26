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
class SimpleBoxConfig(SimpleFsspecConfig):
    pass


class BoxIngestDoc(FsspecIngestDoc):
    @requires_dependencies(["boxfs", "fsspec"], extras="box")
    def get_file(self):
        super().get_file()


@requires_dependencies(["boxfs", "fsspec"], extras="box")
class BoxConnector(FsspecConnector):
    ingest_doc_cls: Type[BoxIngestDoc] = BoxIngestDoc

    def __init__(
        self,
        config: SimpleBoxConfig,
        standard_config: StandardConnectorConfig,
    ) -> None:
        super().__init__(standard_config, config)
