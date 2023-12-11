import typing as t
from dataclasses import dataclass

import click

from unstructured.ingest.cli.base.src import BaseSrcCmd
from unstructured.ingest.cli.interfaces import (
    CliConfig,
)
from unstructured.ingest.connector.fsspec.sftp import SimpleSftpConfig

CMD_NAME = "sftp"


@dataclass
class SftpCliConfig(SimpleSftpConfig, CliConfig):
    @staticmethod
    def get_cli_options() -> t.List[click.Option]:
        options = [
            click.Option(
                ["--username"],
                required=True,
                type=str,
                help="Username for sftp connection",
            ),
            click.Option(
                ["--password"],
                required=True,
                type=str,
                help="Password for sftp connection",
            ),
        ]
        return options


def get_base_src_cmd() -> BaseSrcCmd:
    cmd_cls = BaseSrcCmd(
        cmd_name=CMD_NAME,
        cli_config=SftpCliConfig,
        is_fsspec=True,
    )
    return cmd_cls
