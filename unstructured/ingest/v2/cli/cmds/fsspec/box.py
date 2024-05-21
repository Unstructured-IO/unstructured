from dataclasses import dataclass

import click

from unstructured.ingest.v2.cli.base import DestCmd, SrcCmd
from unstructured.ingest.v2.cli.cmds.fsspec.fsspec import (
    FsspecCliDownloadConfig,
    FsspecCliIndexerConfig,
    FsspecCliUploaderConfig,
)
from unstructured.ingest.v2.cli.interfaces import CliConfig
from unstructured.ingest.v2.processes.connectors.fsspec.box import (
    CONNECTOR_TYPE,
)


@dataclass
class BoxCliDownloadConfig(FsspecCliDownloadConfig):
    pass


@dataclass
class BoxCliIndexerConfig(FsspecCliIndexerConfig):
    pass


@dataclass
class BoxCliConnectionConfig(CliConfig):
    @staticmethod
    def get_cli_options() -> list[click.Option]:
        options = [
            click.Option(
                ["--box-app-config"],
                default=None,
                type=click.Path(),
                help="Path to Box app credentials as json file.",
            ),
        ]
        return options


@dataclass
class BoxUploaderConfig(FsspecCliUploaderConfig):
    pass


box_src_cmd = SrcCmd(
    cmd_name=CONNECTOR_TYPE,
    indexer_config=BoxCliIndexerConfig,
    connection_config=BoxCliConnectionConfig,
    downloader_config=BoxCliDownloadConfig,
)

box_dest_cmd = DestCmd(
    cmd_name=CONNECTOR_TYPE,
    connection_config=BoxCliConnectionConfig,
    uploader_config=BoxUploaderConfig,
)
