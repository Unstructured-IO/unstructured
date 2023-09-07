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
)
from unstructured.ingest.interfaces import BaseConfig
from unstructured.ingest.logger import ingest_log_streaming_init, logger
from unstructured.ingest.runner import delta_table as delta_table_fn


@dataclass
class DeltaTableCliConfig(BaseConfig, CliMixin):
    table_uri: str
    version: t.Optional[int] = None
    storage_options: t.Optional[str] = None
    without_files: bool = False

    @staticmethod
    def add_cli_options(cmd: click.Command) -> None:
        options = [
            click.Option(
                ["--table-uri"],
                required=True,
                help="the path of the DeltaTable",
            ),
            click.Option(
                ["--version"],
                default=None,
                type=int,
                help="version of the DeltaTable",
            ),
            click.Option(
                ["--storage_options"],
                required=False,
                type=str,
                help="a dictionary of the options to use for the storage backend, "
                "format='value1=key1,value2=key2'",
            ),
            click.Option(
                ["--without-files"],
                is_flag=True,
                default=False,
                help="If set, will load table without tracking files.",
            ),
        ]
        cmd.params.extend(options)


@click.group(name="delta-table", invoke_without_command=True, cls=Group)
@click.pass_context
def delta_table_source(ctx: click.Context, **options):
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
        DeltaTableCliConfig.from_dict(options)
        delta_table_fn(read_config=read_config, partition_config=partition_config, **options)
    except Exception as e:
        logger.error(e, exc_info=True)
        raise click.ClickException(str(e)) from e


def get_source_cmd() -> click.Group:
    cmd = delta_table_source
    DeltaTableCliConfig.add_cli_options(cmd)

    # Common CLI configs
    CliReadConfig.add_cli_options(cmd)
    CliPartitionConfig.add_cli_options(cmd)
    cmd.params.append(click.Option(["-v", "--verbose"], is_flag=True, default=False))
    return cmd
