import logging
import typing as t
from dataclasses import dataclass

import click

from unstructured.ingest.cli.cmds.utils import (
    DelimitedString,
    Group,
    conform_click_options,
)
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
from unstructured.ingest.runner import discord as discord_fn


@dataclass
class DiscordCliConfig(BaseConfig, CliMixin):
    channels: t.List[str]
    token: str
    period: t.Optional[int] = None

    @staticmethod
    def add_cli_options(cmd: click.Command) -> None:
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
        cmd.params.extend(options)


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
        # run_init_checks(**options)
        read_config = CliReadConfig.from_dict(options)
        partition_config = CliPartitionConfig.from_dict(options)
        # Run for schema validation
        DiscordCliConfig.from_dict(options)
        discord_fn(read_config=read_config, partition_config=partition_config, **options)
    except Exception as e:
        logger.error(e, exc_info=True)
        raise click.ClickException(str(e)) from e


def get_source_cmd() -> click.Group:
    cmd = discord_source
    DiscordCliConfig.add_cli_options(cmd)

    # Common CLI configs
    CliReadConfig.add_cli_options(cmd)
    CliPartitionConfig.add_cli_options(cmd)
    cmd.params.append(click.Option(["-v", "--verbose"], is_flag=True, default=False))
    return cmd
