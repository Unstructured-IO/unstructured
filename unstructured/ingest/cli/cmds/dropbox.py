import typing as t
from dataclasses import dataclass

import click

from unstructured.ingest.cli.cmds.base_cmd import BaseCmd
from unstructured.ingest.cli.interfaces import (
    CliMixin,
)
from unstructured.ingest.interfaces import BaseConfig


@dataclass
class DropboxCliConfig(BaseConfig, CliMixin):
    token: str

    @staticmethod
    def get_cli_options() -> t.List[click.Option]:
        options = [
            click.Option(
                ["--token"],
                required=True,
                help="Dropbox access token.",
            ),
        ]
        return options


def get_base_cmd() -> BaseCmd:
    cmd_cls = BaseCmd(cmd_name="dropbox", cli_config=DropboxCliConfig, is_fsspec=True)
    return cmd_cls
