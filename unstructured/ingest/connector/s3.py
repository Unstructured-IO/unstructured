from dataclasses import dataclass

from unstructured.ingest.connector.fsspec import (
    SimpleFsspecConfig,
    FsspecIngestDoc,
    FsspecConnector,
)
from unstructured.utils import requires_dependencies


@dataclass
class SimpleS3Config(SimpleFsspecConfig):
    pass


class S3IngestDoc(FsspecIngestDoc):
    @requires_dependencies(["s3fs", "fsspec"], extras="s3")
    def get_file(self):
        super().get_file()


@requires_dependencies(["s3fs", "fsspec"], extras="s3")
class S3Connector(FsspecConnector):
    pass
