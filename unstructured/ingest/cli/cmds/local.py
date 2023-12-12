import typing as t
from dataclasses import dataclass

import click

from unstructured.ingest.cli.base.src import BaseSrcCmd
from unstructured.ingest.cli.interfaces import (
    CliConfig,
    CliRecursiveConfig,
    DelimitedString,
)
from unstructured.ingest.connector.local import SimpleLocalConfig


@dataclass
class LocalCliConfig(SimpleLocalConfig, CliConfig):
    @staticmethod
    def get_cli_options() -> t.List[click.Option]:
        options = [
            click.Option(
                ["--input-path"],
                required=True,
                type=click.Path(file_okay=True, dir_okay=True, exists=True),
                help="Path to the location in the local file system that will be processed.",
            ),
            click.Option(
                ["--file-glob"],
                default=None,
                type=DelimitedString(),
                help="A comma-separated list of file globs to limit which types of "
                "local files are accepted, e.g. '*.html,*.txt'",
            ),
        ]
        return options


def get_base_src_cmd() -> BaseSrcCmd:
    cmd_cls = BaseSrcCmd(
        cmd_name="local",
        cli_config=LocalCliConfig,
        additional_cli_options=[CliRecursiveConfig],
    )
    return cmd_cls
