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


@dataclass
class DeltaTableCliWriteConfig(BaseConfig, CliMixin):
    write_column: str
    mode: t.Literal["error", "append", "overwrite", "ignore"] = "error"

    @staticmethod
    def add_cli_options(cmd: click.Command) -> None:
        options = [
            click.Option(
                ["--write-column"],
                required=True,
                type=str,
                help="column in delta table to write json content",
            ),
            click.Option(
                ["--mode"],
                default="error",
                type=click.Choice(["error", "append", "overwrite", "ignore"]),
                help="How to handle existing data. Default is to error if table already exists. "
                "If 'append', will add new data. "
                "If 'overwrite', will replace table with new data. "
                "If 'ignore', will not write anything if table already exists.",
            ),
        ]
        cmd.params.extend(options)


@click.command(name="delta-table")
@click.pass_context
def delta_table_dest(ctx: click.Context, **options):
    parent_options: dict = ctx.parent.params if ctx.parent else {}
    # Click sets all multiple fields as tuple, this needs to be updated to list
    for k, v in options.items():
        if isinstance(v, tuple):
            options[k] = list(v)
    for k, v in parent_options.items():
        if isinstance(v, tuple):
            parent_options[k] = list(v)
    verbose = parent_options.get("verbose", False)
    ingest_log_streaming_init(logging.DEBUG if verbose else logging.INFO)
    log_options(parent_options, verbose=verbose)
    log_options(options, verbose=verbose)
    try:
        # run_init_checks(**options)
        read_config = CliReadConfig.from_dict(parent_options)
        partition_config = CliPartitionConfig.from_dict(parent_options)
        # Run for schema validation
        DeltaTableCliConfig.from_dict(options)
        DeltaTableCliWriteConfig.from_dict(options)
        delta_table_fn(
            read_config=read_config,
            partition_config=partition_config,
            writer_type="delta_table",
            writer_kwargs=options,
            **parent_options,
        )
    except Exception as e:
        logger.error(e, exc_info=True)
        raise click.ClickException(str(e)) from e


def get_dest_cmd() -> click.Command:
    cmd = delta_table_dest
    DeltaTableCliConfig.add_cli_options(cmd)
    DeltaTableCliWriteConfig.add_cli_options(cmd)
    return cmd


def get_source_cmd() -> click.Group:
    cmd = delta_table_source
    DeltaTableCliConfig.add_cli_options(cmd)

    # Common CLI configs
    CliReadConfig.add_cli_options(cmd)
    CliPartitionConfig.add_cli_options(cmd)
    cmd.params.append(click.Option(["-v", "--verbose"], is_flag=True, default=False))
    return cmd
