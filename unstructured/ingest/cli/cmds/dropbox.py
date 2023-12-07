import typing as t
from dataclasses import dataclass

import click

from unstructured.ingest.cli.base.src import BaseSrcCmd
from unstructured.ingest.cli.interfaces import (
    CliConfig,
)
from unstructured.ingest.connector.dropbox import (
    DropboxAccessConfig,
    DropboxWriteConfig,
    SimpleDropboxConfig,
)

CMD_NAME = "dropbox"


@dataclass
class DropboxCliConfig(DropboxAccessConfig, CliConfig):
    @staticmethod
    def get_cli_options() -> t.List[click.Option]:
        options = [
            click.Option(
                ["--token"],
                required=True,
                type=str,
                help="Dropbox access token.",
            ),
        ]
        return options


def get_base_src_cmd() -> BaseSrcCmd:
    cmd_cls = BaseSrcCmd(
        cmd_name=CMD_NAME,
        cli_config=DropboxCliConfig,
        addition_configs={"connector_config": SimpleDropboxConfig},
        is_fsspec=True,
    )
    return cmd_cls


def get_base_dest_cmd():
    from unstructured.ingest.cli.base.dest import BaseDestCmd

    cmd_cls = BaseDestCmd(
        cmd_name=CMD_NAME,
        cli_config=DropboxCliConfig,
        addition_configs={
            "connector_config": SimpleDropboxConfig,
            "write_config": DropboxWriteConfig,
        },
        is_fsspec=True,
    )
    return cmd_cls
