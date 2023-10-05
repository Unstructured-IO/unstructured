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
from unstructured.ingest.runner import slack as slack_fn


@dataclass
class SlackCliConfig(BaseConfig, CliMixin):
    token: str
    channels: t.List[str]
    start_date: t.Optional[str] = None
    end_date: t.Optional[str] = None

    @staticmethod
    def add_cli_options(cmd: click.Command) -> None:
        options = [
            click.Option(
                ["--token"],
                required=True,
                type=str,
                help="Bot token used to access Slack API, must have channels:history "
                "scope for the bot user",
            ),
            click.Option(
                ["--channels"],
                required=True,
                type=DelimitedString(),
                help="Comma-delimited list of Slack channel IDs to pull messages from, "
                "can be a public or private channel",
            ),
            click.Option(
                ["--start-date"],
                default=None,
                type=str,
                help="Start date/time in formats YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS or "
                "YYYY-MM-DD+HH:MM:SS or YYYY-MM-DDTHH:MM:SStz",
            ),
            click.Option(
                ["--end-date"],
                default=None,
                type=str,
                help="End date/time in formats YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS or "
                "YYYY-MM-DD+HH:MM:SS or YYYY-MM-DDTHH:MM:SStz",
            ),
        ]
        cmd.params.extend(options)


@click.group(name="slack", invoke_without_command=True, cls=Group)
@click.pass_context
def slack_source(ctx: click.Context, **options):
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
        SlackCliConfig.from_dict(options)
        slack_fn(read_config=read_config, partition_config=partition_config, **options)
    except Exception as e:
        logger.error(e, exc_info=True)
        raise click.ClickException(str(e)) from e


def get_source_cmd() -> click.Group:
    cmd = slack_source
    SlackCliConfig.add_cli_options(cmd)

    # Common CLI configs
    CliReadConfig.add_cli_options(cmd)
    CliPartitionConfig.add_cli_options(cmd)
    cmd.params.append(click.Option(["-v", "--verbose"], is_flag=True, default=False))
    return cmd
