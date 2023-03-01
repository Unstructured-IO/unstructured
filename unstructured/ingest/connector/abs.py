from dataclasses import dataclass

from unstructured.ingest.connector.fsspec import (
    SimpleFsspecConfig,
    FsspecIngestDoc,
    FsspecConnector,
)
from unstructured.utils import requires_dependencies


@dataclass
class SimpleABSConfig(SimpleFsspecConfig):
    pass


class ABSIngestDoc(FsspecIngestDoc):
    @requires_dependencies(["adlfs", "fsspec"], extras="azure")
    def get_file(self):
        super().get_file()


@requires_dependencies(["adlfs", "fsspec"], extras="azure")
class ABSConnector(FsspecConnector):
    pass
