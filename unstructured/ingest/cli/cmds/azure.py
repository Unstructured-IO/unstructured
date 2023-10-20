import logging
import typing as t
from dataclasses import dataclass

import click

from unstructured.ingest.cli.common import (
    log_options,
)
from unstructured.ingest.cli.interfaces import (
    CliFilesStorageConfig,
    CliMixin,
)
from unstructured.ingest.cli.utils import Group, add_options, conform_click_options, extract_configs
from unstructured.ingest.interfaces import BaseConfig, FsspecConfig
from unstructured.ingest.logger import ingest_log_streaming_init, logger
from unstructured.ingest.runner import AzureRunner


@dataclass
class AzureCliConfig(BaseConfig, CliMixin):
    account_id: t.Optional[str] = None
    account_name: t.Optional[str] = None
    connection_string: t.Optional[str] = None

    @staticmethod
    def get_cli_options() -> t.List[click.Option]:
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
        return options


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
        configs = extract_configs(
            options,
            validate=[AzureCliConfig],
            extras={"fsspec_config": FsspecConfig},
        )
        runner = AzureRunner(
            **configs,  # type: ignore
        )
        runner.run(**options)
    except Exception as e:
        logger.error(e, exc_info=True)
        raise click.ClickException(str(e)) from e


def get_source_cmd() -> click.Group:
    cmd = azure_source
    add_options(cmd, extras=[AzureCliConfig, CliFilesStorageConfig])
    return cmd
