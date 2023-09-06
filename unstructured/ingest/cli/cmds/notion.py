import logging
import typing as t
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
    CliRecursiveConfig,
)
from unstructured.ingest.interfaces import BaseConfig
from unstructured.ingest.logger import ingest_log_streaming_init, logger
from unstructured.ingest.runner import notion as notion_fn


@dataclass
class NotionCliConfigs(BaseConfig, CliMixin):
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
                multiple=True,
                type=str,
                help="Notion page IDs to pull text from",
            ),
            click.Option(
                ["--database-ids"],
                default=None,
                multiple=True,
                type=str,
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
        read_configs = CliReadConfig.from_dict(options)
        partition_configs = CliPartitionConfig.from_dict(options)
        # Run for schema validation
        NotionCliConfigs.from_dict(options)
        notion_fn(read_config=read_configs, partition_configs=partition_configs, **options)
    except Exception as e:
        logger.error(e, exc_info=True)
        raise click.ClickException(str(e)) from e


def get_source_cmd() -> click.Group:
    cmd = notion_source
    NotionCliConfigs.add_cli_options(cmd)
    CliRecursiveConfig.add_cli_options(cmd)

    # Common CLI configs
    CliReadConfig.add_cli_options(cmd)
    CliPartitionConfig.add_cli_options(cmd)
    cmd.params.append(click.Option(["-v", "--verbose"], is_flag=True, default=False))
    return cmd
