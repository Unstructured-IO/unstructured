"""
Dropbox Connector
The Dropbox Connector presents a couple abnormal situations.
1) They don't have an unexpiring token
2) They require a forward slash `/` in front of the remote_file_path. This presents
some real problems creating paths. When appending a path that begins with a
forward slash to any path, whether using the / shorthand or joinpath, causes the
starting path to disappear. So the `/` needs to be stripped off.
3) To list and get files from the root directory Dropbox you need a ""," ", or " /"
"""
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Type

from unstructured.ingest.connector.fsspec import (
    FsspecDestinationConnector,
    FsspecIngestDoc,
    FsspecSourceConnector,
    SimpleFsspecConfig,
)
from unstructured.ingest.error import SourceConnectionError
from unstructured.utils import requires_dependencies


class MissingFolderError(Exception):
    """There is no folder by that name. For root try `dropbox:// /`"""


@dataclass
class SimpleDropboxConfig(SimpleFsspecConfig):
    pass


@dataclass
class DropboxIngestDoc(FsspecIngestDoc):
    connector_config: SimpleDropboxConfig
    registry_name: str = "dropbox"

    @SourceConnectionError.wrap
    @requires_dependencies(["dropboxdrivefs", "fsspec"], extras="dropbox")
    def get_file(self):
        super().get_file()

    @property
    def _output_filename(self):
        # Dropbox requires a forward slash at the front of the folder path. This
        # creates some complications in path joining so a custom path is created here.
        # Dropbox uses an empty string `""`, or a space `" "`` or a `" /"` to list root
        if self.connector_config.dir_path == " ":
            return Path(self.processor_config.output_dir) / re.sub(
                "^/",
                "",
                f"{self.remote_file_path}.json",
            )
        else:
            return (
                Path(self.processor_config.output_dir)
                / f"{self.remote_file_path.replace(f'/{self.connector_config.dir_path}/', '')}.json"
            )

    def _tmp_download_file(self):
        # Dropbox requires a forward slash at the front of the folder path. This
        # creates some complications in path joining so a custom path is created here.
        # Dropbox uses an empty string `""`, or a space `" "`` or a `" /"` to list root
        download_dir: str = self.read_config.download_dir if self.read_config.download_dir else ""
        if not download_dir:
            return ""
        if self.connector_config.dir_path == " ":
            return Path(download_dir) / re.sub(
                "^/",
                "",
                self.remote_file_path,
            )
        else:
            return Path(download_dir) / self.remote_file_path.replace(
                f"/{self.connector_config.dir_path}/",
                "",
            )


@dataclass
class DropboxSourceConnector(FsspecSourceConnector):
    connector_config: SimpleDropboxConfig

    def __post_init__(self):
        self.ingest_doc_cls: Type[DropboxIngestDoc] = DropboxIngestDoc

    @requires_dependencies(["dropboxdrivefs", "fsspec"], extras="dropbox")
    def initialize(self):
        from fsspec import AbstractFileSystem, get_filesystem_class

        self.fs: AbstractFileSystem = get_filesystem_class(self.connector_config.protocol)(
            **self.connector_config.get_access_kwargs(),
        )
        # Dropbox requires a forward slash at the front of the folder path. This
        # creates some complications in path joining so a custom path is created here.
        ls_output = self.fs.ls(f"/{self.connector_config.path_without_protocol}")
        if ls_output and len(ls_output) >= 1:
            return
        elif ls_output:
            raise ValueError(
                f"No objects found in {self.connector_config.remote_url}.",
            )
        else:
            raise MissingFolderError(
                "There is no folder by that name. For root try `dropbox:// /`",
            )

    def _list_files(self):
        # Dropbox requires a forward slash at the front of the folder path. This
        # creates some complications in path joining so a custom path is created here.
        if not self.connector_config.recursive:
            # fs.ls does not walk directories
            # directories that are listed in cloud storage can cause problems because they are seen
            # as 0byte files
            return [
                x.get("name")
                for x in self.fs.ls(
                    f"/{self.connector_config.path_without_protocol}",
                    detail=True,
                )
                if x.get("size")
            ]
        else:
            # fs.find will recursively walk directories
            # "size" is a common key for all the cloud protocols with fs
            return [
                k
                for k, v in self.fs.find(
                    f"/{self.connector_config.path_without_protocol}",
                    detail=True,
                ).items()
                if v.get("size")
            ]


@dataclass
class DropboxDestinationConnector(FsspecDestinationConnector):
    connector_config: SimpleFsspecConfig
