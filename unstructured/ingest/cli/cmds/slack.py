import typing as t
from dataclasses import dataclass

import click

from unstructured.ingest.cli.base.src import BaseSrcCmd
from unstructured.ingest.cli.interfaces import (
    CliConfig,
    DelimitedString,
)


@dataclass
class SlackCliConfig(CliConfig):
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


def get_base_src_cmd() -> BaseSrcCmd:
    cmd_cls = BaseSrcCmd(cmd_name="slack", cli_config=SlackCliConfig)
    return cmd_cls
