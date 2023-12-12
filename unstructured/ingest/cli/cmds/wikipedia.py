import typing as t
from dataclasses import dataclass

import click

from unstructured.ingest.cli.base.src import BaseSrcCmd
from unstructured.ingest.cli.interfaces import (
    CliConfig,
)
from unstructured.ingest.connector.wikipedia import SimpleWikipediaConfig


@dataclass
class WikipediaCliConfig(SimpleWikipediaConfig, CliConfig):
    @staticmethod
    def get_cli_options() -> t.List[click.Option]:
        options = [
            click.Option(
                ["--page-title"],
                required=True,
                type=str,
                help='Title of a Wikipedia page, e.g. "Open source software".',
            ),
            click.Option(
                ["--auto-suggest"],
                default=True,
                is_flag=True,
                help="Whether to automatically suggest a page if the exact page was not found."
                " Set to False if the wrong Wikipedia page is fetched.",
            ),
        ]
        return options


def get_base_src_cmd() -> BaseSrcCmd:
    cmd_cls = BaseSrcCmd(
        cmd_name="wikipedia",
        cli_config=WikipediaCliConfig,
    )
    return cmd_cls
