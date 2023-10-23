import logging
import typing as t
from dataclasses import dataclass

import click

from unstructured.ingest.cli.common import (
    log_options,
)
from unstructured.ingest.cli.interfaces import (
    CliMixin,
    DelimitedString,
)
from unstructured.ingest.cli.utils import Group, add_options, conform_click_options, extract_configs
from unstructured.ingest.interfaces import BaseConfig
from unstructured.ingest.logger import ingest_log_streaming_init, logger
from unstructured.ingest.runner import DiscordRunner


@dataclass
class DiscordCliConfig(BaseConfig, CliMixin):
    channels: t.List[str]
    token: str
    period: t.Optional[int] = None

    @staticmethod
    def get_cli_options() -> t.List[click.Option]:
        options = [
            click.Option(
                ["--token"],
                required=True,
                help="Bot token used to access Discord API, must have "
                "READ_MESSAGE_HISTORY scope for the bot user",
            ),
            click.Option(
                ["--channels"],
                required=True,
                type=DelimitedString(),
                help="Comma-delimited list of discord channel ids to ingest from.",
            ),
            click.Option(
                ["--period"],
                default=None,
                help="Number of days to go back in the history of "
                "discord channels, must be a number",
            ),
        ]
        return options


@click.group(name="discord", invoke_without_command=True, cls=Group)
@click.pass_context
def discord_source(ctx: click.Context, **options):
    if ctx.invoked_subcommand:
        return

    conform_click_options(options)
    verbose = options.get("verbose", False)
    ingest_log_streaming_init(logging.DEBUG if verbose else logging.INFO)
    log_options(options, verbose=verbose)
    try:
        configs = extract_configs(options, validate=[DiscordCliConfig])
        runner = DiscordRunner(
            **configs,  # type: ignore
        )
        runner.run(**options)
    except Exception as e:
        logger.error(e, exc_info=True)
        raise click.ClickException(str(e)) from e


def get_source_cmd() -> click.Group:
    cmd = discord_source
    add_options(cmd, extras=[DiscordCliConfig])
    return cmd
