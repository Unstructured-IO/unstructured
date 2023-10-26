import typing as t
from dataclasses import dataclass

import click

from unstructured.ingest.cli.base.src import BaseSrcCmd
from unstructured.ingest.cli.interfaces import (
    CliMixin,
)
from unstructured.ingest.interfaces import BaseConfig


@dataclass
class BoxCliConfig(BaseConfig, CliMixin):
    box_app_config: t.Optional[str] = None

    @staticmethod
    def get_cli_options() -> t.List[click.Option]:
        options = [
            click.Option(
                ["--box-app-config"],
                default=None,
                help="Path to Box app credentials as json file.",
            ),
        ]
        return options


def get_base_src_cmd() -> BaseSrcCmd:
    cmd_cls = BaseSrcCmd(cmd_name="box", cli_config=BoxCliConfig, is_fsspec=True)
    return cmd_cls
