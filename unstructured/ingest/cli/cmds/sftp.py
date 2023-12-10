import typing as t
from dataclasses import dataclass

import click

from unstructured.ingest.cli.base.src import BaseSrcCmd
from unstructured.ingest.cli.interfaces import (
    CliConfig,
)
from unstructured.ingest.connector.sftp import SftpAccessConfig, SimpleSftpConfig

CMD_NAME = "sftp"


@dataclass
class SftpCliConfig(SftpAccessConfig, CliConfig):
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
        addition_configs={"fsspec_config": SimpleSftpConfig},
        is_fsspec=True,
    )
    return cmd_cls
