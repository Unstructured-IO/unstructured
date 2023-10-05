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
    CliRecursiveConfig,
)
from unstructured.ingest.interfaces import BaseConfig
from unstructured.ingest.logger import ingest_log_streaming_init, logger
from unstructured.ingest.runner import notion as notion_fn


@dataclass
class NotionCliConfig(BaseConfig, CliMixin):
    api_key: str
    page_ids: t.Optional[t.List[str]]
    database_ids: t.Optional[t.List[str]]

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
        # run_init_checks(**options)
        read_config = CliReadConfig.from_dict(options)
        partition_config = CliPartitionConfig.from_dict(options)
        # Run for schema validation
        NotionCliConfig.from_dict(options)
        notion_fn(read_config=read_config, partition_config=partition_config, **options)
    except Exception as e:
        logger.error(e, exc_info=True)
        raise click.ClickException(str(e)) from e


def get_source_cmd() -> click.Group:
    cmd = notion_source
    NotionCliConfig.add_cli_options(cmd)
    CliRecursiveConfig.add_cli_options(cmd)

    # Common CLI configs
    CliReadConfig.add_cli_options(cmd)
    CliPartitionConfig.add_cli_options(cmd)
    cmd.params.append(click.Option(["-v", "--verbose"], is_flag=True, default=False))
    return cmd
