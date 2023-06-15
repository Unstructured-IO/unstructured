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
class SimpleDropboxConfig(SimpleFsspecConfig):
    pass


class DropboxIngestDoc(FsspecIngestDoc):
    @requires_dependencies(["dropboxdrivefs", "fsspec"])
    def get_file(self):
        super().get_file()


@requires_dependencies(["dropboxdrivefs", "fsspec"])
class DropboxConnector(FsspecConnector):
    ingest_doc_cls: Type[DropboxIngestDoc] = DropboxIngestDoc

    def __init__(
        self,
        config: SimpleDropboxConfig,
        standard_config: StandardConnectorConfig,
    ) -> None:
        super().__init__(standard_config, config)

    def find_files(self, directory):
        """Recursively returns the files in a bucket since fs.ls is only one level deep."""
        file_paths = []

        def add_files(directory):
            for blob in self.fs.ls(directory, detail=True):
                if blob.get("type") == "directory":
                    add_files(blob.get("name"))
                elif blob.get("type") == "file" and blob.get("size") > 0:
                    file_paths.append(blob.get("name"))

        add_files(directory)

        return file_paths

    # def _list_files(self):
    #     """Override the fsspec.py _list_files"""
    #     return self.find_files(self.config.path_without_protocol)


"""
unstructured-ingest \
   --remote-url gs://unstructured_public/ \
   --structured-output-dir dropbox-output \
   --num-processes 2 \
   --verbose 

unstructured-ingest \
   --dropbox-folder /test_folder \
   --dropbox-token  sl.BgNqyiTA9HlYjM0bb7EAh-BhzBdqCokmqkNyuxKarE32gY2rg5Y8DjSD04-8xxrKLaNXseU2KSw35g1OL345RRtyHIrHYEb29vIkSpGR7CtA9AC9Q2NHuhCV4eIUnIrVs2f6vlMk\
   --structured-output-dir dropbox-output \
   --download-dir dropbox-download
   --num-processes 2 \
   --verbose 

   
PYTHONPATH=. ./unstructured/ingest/main.py \
   --metadata-exclude metadata.data_source.date_processed \
   --discord-channels 1099442333440802930,1099601456321003600 \
   --discord-token "$DISCORD_TOKEN" \
   --download-dir discord-ingest-download \
   --structured-output-dir discord-ingest-output \
   --reprocess
"""
