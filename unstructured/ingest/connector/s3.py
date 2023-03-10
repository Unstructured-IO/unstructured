from dataclasses import dataclass
from typing import Type

from unstructured.ingest.connector.fsspec import (
    FsspecConnector,
    FsspecIngestDoc,
    SimpleFsspecConfig,
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
    ingest_doc_cls: Type[S3IngestDoc] = S3IngestDoc

    def __init__(
        self,
        config: SimpleS3Config,
    ) -> None:
        super().__init__(config=config)
