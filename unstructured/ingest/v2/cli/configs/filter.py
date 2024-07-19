from dataclasses import dataclass

import click

from unstructured.ingest.v2.cli.interfaces import CliConfig
from unstructured.ingest.v2.cli.utils import DelimitedString


@dataclass
class FilterCliConfig(CliConfig):
    @staticmethod
    def get_cli_options() -> list[click.Option]:
        options = [
            click.Option(
                ["--file-glob"],
                default=None,
                type=DelimitedString(),
                help="A comma-separated list of file globs to limit which types of "
                "local files are accepted, e.g. '*.html,*.txt'",
            ),
            click.Option(
                ["--max-file-size"],
                default=None,
                type=click.IntRange(min=1),
                help="Max file size to process in bytes",
            ),
        ]
        return options
