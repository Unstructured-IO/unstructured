import logging
import typing as t
from dataclasses import dataclass

import click

from unstructured.ingest.cli.common import (
    log_options,
)
from unstructured.ingest.cli.interfaces import (
    CliMixin,
    CliRecursiveConfig,
    DelimitedString,
)
from unstructured.ingest.cli.utils import Group, add_options, conform_click_options, extract_configs
from unstructured.ingest.interfaces import BaseConfig
from unstructured.ingest.logger import ingest_log_streaming_init, logger
from unstructured.ingest.runner import NotionRunner


@dataclass
class NotionCliConfig(BaseConfig, CliMixin):
    api_key: str
    page_ids: t.Optional[t.List[str]]
    database_ids: t.Optional[t.List[str]]
    max_retries: t.Optional[int] = None
    max_time: t.Optional[float] = None

    @staticmethod
    def add_cli_options(cmd: click.Command) -> None:
        options = [
            click.Option(
                ["--api-key"],
                required=True,
                type=str,
                help="API key for Notion api",
            ),
            click.Option(
                ["--page-ids"],
                default=None,
                type=DelimitedString(),
                help="Notion page IDs to pull text from",
            ),
            click.Option(
                ["--database-ids"],
                default=None,
                type=DelimitedString(),
                help="Notion database IDs to pull text from",
            ),
            click.Option(
                ["--max-retries"],
                default=None,
                type=int,
                help="If provided, will use this max retry for "
                "back off strategy if http calls fail",
            ),
            click.Option(
                ["--max-time"],
                default=None,
                type=float,
                help="If provided, will attempt retries for this long as part "
                "of back off strategy if http calls fail",
            ),
        ]
        cmd.params.extend(options)


@click.group(name="notion", invoke_without_command=True, cls=Group)
@click.pass_context
def notion_source(ctx: click.Context, **options):
    if ctx.invoked_subcommand:
        return

    conform_click_options(options)
    verbose = options.get("verbose", False)
    ingest_log_streaming_init(logging.DEBUG if verbose else logging.INFO)
    log_options(options, verbose=verbose)
    try:
        configs = extract_configs(options, validate=([NotionCliConfig]))
        runner = NotionRunner(
            **configs,  # type: ignore
        )
        runner.run(**options)
    except Exception as e:
        logger.error(e, exc_info=True)
        raise click.ClickException(str(e)) from e


def get_source_cmd() -> click.Group:
    cmd = notion_source
    add_options(cmd, extras=[NotionCliConfig, CliRecursiveConfig])
    return cmd
