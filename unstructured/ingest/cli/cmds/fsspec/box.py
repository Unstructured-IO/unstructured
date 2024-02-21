import typing as t
from dataclasses import dataclass

import click

from unstructured.ingest.cli.base.src import BaseSrcCmd
from unstructured.ingest.cli.interfaces import (
    CliConfig,
)
from unstructured.ingest.connector.fsspec.box import BoxWriteConfig, SimpleBoxConfig

CMD_NAME = "box"


@dataclass
class BoxCliConfig(SimpleBoxConfig, CliConfig):
    @staticmethod
    def get_cli_options() -> t.List[click.Option]:
        options = [
            click.Option(
                ["--box-app-config"],
                default=None,
                type=click.Path(),
                help="Path to Box app credentials as json file.",
            ),
        ]
        return options


def get_base_src_cmd() -> BaseSrcCmd:
    cmd_cls = BaseSrcCmd(
        cmd_name=CMD_NAME,
        cli_config=BoxCliConfig,
        is_fsspec=True,
    )
    return cmd_cls


def get_base_dest_cmd():
    from unstructured.ingest.cli.base.dest import BaseDestCmd

    cmd_cls = BaseDestCmd(
        cmd_name=CMD_NAME,
        cli_config=BoxCliConfig,
        write_config=BoxWriteConfig,
        is_fsspec=True,
    )
    return cmd_cls
