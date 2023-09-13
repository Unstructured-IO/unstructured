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
    CliRemoteUrlConfig,
)
from unstructured.ingest.interfaces import BaseConfig
from unstructured.ingest.logger import ingest_log_streaming_init, logger
from unstructured.ingest.runner import azure as azure_fn


@dataclass
class AzureCliConfig(BaseConfig, CliMixin):
    account_id: t.Optional[str] = None
    account_name: t.Optional[str] = None
    connection_string: t.Optional[str] = None

    @staticmethod
    def add_cli_options(cmd: click.Command) -> None:
        options = [
            click.Option(
                ["--account-key"],
                default=None,
                help="Azure Blob Storage or DataLake account key (not required if "
                "`azure_account_name` is public).",
            ),
            click.Option(
                ["--account-name"],
                default=None,
                help="Azure Blob Storage or DataLake account name.",
            ),
            click.Option(
                ["--connection-string"],
                default=None,
                help="Azure Blob Storage or DataLake connection string.",
            ),
        ]
        cmd.params.extend(options)


@click.group(name="azure", invoke_without_command=True, cls=Group)
@click.pass_context
def azure_source(ctx: click.Context, **options):
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
        AzureCliConfig.from_dict(options)
        azure_fn(read_config=read_config, partition_config=partition_config, **options)
    except Exception as e:
        logger.error(e, exc_info=True)
        raise click.ClickException(str(e)) from e


def get_source_cmd() -> click.Group:
    cmd = azure_source
    AzureCliConfig.add_cli_options(cmd)
    CliRemoteUrlConfig.add_cli_options(cmd)
    CliRecursiveConfig.add_cli_options(cmd)

    # Common CLI configs
    CliReadConfig.add_cli_options(cmd)
    CliPartitionConfig.add_cli_options(cmd)
    cmd.params.append(click.Option(["-v", "--verbose"], is_flag=True, default=False))
    return cmd
