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
from unstructured.ingest.runner import SlackRunner


@dataclass
class SlackCliConfig(BaseConfig, CliMixin):
    token: str
    channels: t.List[str]
    start_date: t.Optional[str] = None
    end_date: t.Optional[str] = None

    @staticmethod
    def get_cli_options() -> t.List[click.Option]:
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
        return options


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
        configs = extract_configs(data=options, validate=[SlackCliConfig])
        sharepoint_runner = SlackRunner(
            **configs,  # type: ignore
        )
        sharepoint_runner.run(**options)
    except Exception as e:
        logger.error(e, exc_info=True)
        raise click.ClickException(str(e)) from e


def get_source_cmd() -> click.Group:
    cmd = slack_source
    add_options(cmd, extras=[SlackCliConfig])
    return cmd
