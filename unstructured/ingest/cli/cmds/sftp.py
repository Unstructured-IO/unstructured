import typing as t
from dataclasses import dataclass

import click

from unstructured.ingest.cli.base.src import BaseSrcCmd
from unstructured.ingest.cli.interfaces import (
    CliConfig,
)

CMD_NAME = "sftp"


@dataclass
class SftpCliConfig(CliConfig):
    sftp_username: t.Optional[str] = None ###### probably required
    sftp_password: t.Optional[str] = None ###### probably required

    @staticmethod
    def get_cli_options() -> t.List[click.Option]:
        options = [
            click.Option(
                ["--sftp-username"],
                default=None,
                help="BLAH BLAH BLAH"
                "BLAH BLAH BLAH",
            ),
            click.Option(
                ["--sftp-password"],
                default=None,
                help="BLAH BLAH BLAH"
                "BLAH BLAH BLAH",
            ),
        ]
        return options


def get_base_src_cmd() -> BaseSrcCmd:
    cmd_cls = BaseSrcCmd(cmd_name=CMD_NAME, cli_config=SftpCliConfig, is_fsspec=True)
    return cmd_cls

