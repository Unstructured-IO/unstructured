from dataclasses import dataclass

from unstructured.ingest.connector.fsspec import (
    SimpleFsspecConfig,
    FsspecIngestDoc,
    FsspecConnector,
)
from unstructured.utils import requires_dependencies


@dataclass
class SimpleGCSConfig(SimpleFsspecConfig):
    pass


class GCSIngestDoc(FsspecIngestDoc):
    @requires_dependencies(["gcsfs", "fsspec"], extras="gcs")
    def get_file(self):
        super().get_file()


@requires_dependencies(["gcsfs", "fsspec"], extras="gcs")
class GCSConnector(FsspecConnector):
    pass
