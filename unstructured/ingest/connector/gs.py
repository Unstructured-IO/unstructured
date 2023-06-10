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

    def find_files(self, directory):
        """Recursively returns the files in a bucket since fs.ls is only one level deep."""
        file_paths = []

        def add_files(directory):
            for blob in self.fs.ls(directory, detail=True):
                if blob.get("type") =="directory":
                    add_files(blob.get("name"))
                elif blob.get("type") == "file" and blob.get("size") > 0:
                    file_paths.append(blob.get("name"))

        add_files(directory)

        return file_paths

    def _list_files(self):
        """Override the fsspec.py _list_files"""
        return self.find_files(self.config.path_without_protocol)




"""
unstructured-ingest \
   --remote-url gs://unstructured_public/ \
   --structured-output-dir gs-small-batch-output \
   --num-processes 2 \
   --verbose 
"""