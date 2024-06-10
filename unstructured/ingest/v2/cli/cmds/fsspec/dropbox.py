from dataclasses import dataclass

import click

from unstructured.ingest.v2.cli.base import DestCmd, SrcCmd
from unstructured.ingest.v2.cli.cmds.fsspec.fsspec import (
    FsspecCliDownloadConfig,
    FsspecCliIndexerConfig,
    FsspecCliUploaderConfig,
)
from unstructured.ingest.v2.cli.interfaces import CliConfig
from unstructured.ingest.v2.processes.connectors.fsspec.dropbox import (
    CONNECTOR_TYPE,
)


@dataclass
class DropboxCliDownloadConfig(FsspecCliDownloadConfig):
    pass


@dataclass
class DropboxCliIndexerConfig(FsspecCliIndexerConfig):
    pass


@dataclass
class DropboxCliConnectionConfig(CliConfig):
    @staticmethod
    def get_cli_options() -> list[click.Option]:
        options = [
            click.Option(
                ["--token"],
                required=True,
                type=str,
                help="Dropbox access token.",
            ),
        ]
        return options


@dataclass
class DropboxUploaderConfig(FsspecCliUploaderConfig):
    pass


dropbox_src_cmd = SrcCmd(
    cmd_name=CONNECTOR_TYPE,
    indexer_config=DropboxCliIndexerConfig,
    connection_config=DropboxCliConnectionConfig,
    downloader_config=DropboxCliDownloadConfig,
)

dropbox_dest_cmd = DestCmd(
    cmd_name=CONNECTOR_TYPE,
    connection_config=DropboxCliConnectionConfig,
    uploader_config=DropboxUploaderConfig,
)
