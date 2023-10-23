import logging
import typing as t
from dataclasses import dataclass

import click

from unstructured.ingest.cli.common import (
    log_options,
)
from unstructured.ingest.cli.interfaces import (
    CliMixin,
)
from unstructured.ingest.cli.utils import Group, add_options, conform_click_options, extract_configs
from unstructured.ingest.interfaces import BaseConfig
from unstructured.ingest.logger import ingest_log_streaming_init, logger
from unstructured.ingest.runner import WikipediaRunner


@dataclass
class WikipediaCliConfig(BaseConfig, CliMixin):
    page_title: str
    auto_suggest: bool = True

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


@click.group(name="wikipedia", invoke_without_command=True, cls=Group)
@click.pass_context
def wikipedia_source(ctx: click.Context, **options):
    if ctx.invoked_subcommand:
        return

    conform_click_options(options)
    verbose = options.get("verbose", False)
    ingest_log_streaming_init(logging.DEBUG if verbose else logging.INFO)
    log_options(options, verbose=verbose)
    try:
        configs = extract_configs(data=options, validate=[WikipediaCliConfig])
        runner = WikipediaRunner(
            **configs,  # type: ignore
        )
        runner.run(**options)
    except Exception as e:
        logger.error(e, exc_info=True)
        raise click.ClickException(str(e)) from e


def get_source_cmd() -> click.Group:
    cmd = wikipedia_source
    add_options(cmd, extras=[WikipediaCliConfig])
    return cmd
