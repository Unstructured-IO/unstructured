import logging
from dataclasses import dataclass

import click

from unstructured.ingest.cli.cmds.utils import Group, conform_click_options
from unstructured.ingest.cli.common import (
    log_options,
)
from unstructured.ingest.cli.interfaces import (
    CliMixin,
    CliPartitionConfig,
    CliReadConfig,
)
from unstructured.ingest.interfaces import BaseConfig
from unstructured.ingest.logger import ingest_log_streaming_init, logger
from unstructured.ingest.runner import wikipedia as wikipedia_fn


@dataclass
class WikipediaCliConfig(BaseConfig, CliMixin):
    page_title: str
    auto_suggest: bool = True

    @staticmethod
    def add_cli_options(cmd: click.Command) -> None:
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
        cmd.params.extend(options)


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
        # run_init_checks(**options)
        read_config = CliReadConfig.from_dict(options)
        partition_config = CliPartitionConfig.from_dict(options)
        # Run for schema validation
        WikipediaCliConfig.from_dict(options)
        wikipedia_fn(read_config=read_config, partition_config=partition_config, **options)
    except Exception as e:
        logger.error(e, exc_info=True)
        raise click.ClickException(str(e)) from e


def get_source_cmd() -> click.Group:
    cmd = wikipedia_source
    WikipediaCliConfig.add_cli_options(cmd)

    # Common CLI configs
    CliReadConfig.add_cli_options(cmd)
    CliPartitionConfig.add_cli_options(cmd)
    cmd.params.append(click.Option(["-v", "--verbose"], is_flag=True, default=False))
    return cmd
