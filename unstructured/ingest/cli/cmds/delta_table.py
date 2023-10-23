import logging
import typing as t
from dataclasses import dataclass

import click

from unstructured.ingest.cli.base.src import BaseSrcCmd
from unstructured.ingest.cli.common import (
    log_options,
)
from unstructured.ingest.cli.interfaces import (
    CliMixin,
)
from unstructured.ingest.cli.utils import (
    conform_click_options,
    orchestrate_runner,
)
from unstructured.ingest.interfaces import BaseConfig
from unstructured.ingest.logger import ingest_log_streaming_init, logger


@dataclass
class DeltaTableCliConfig(BaseConfig, CliMixin):
    table_uri: str
    version: t.Optional[int] = None
    storage_options: t.Optional[str] = None
    without_files: bool = False

    @staticmethod
    def get_cli_options() -> t.List[click.Option]:
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
        return options


@dataclass
class DeltaTableCliWriteConfig(BaseConfig, CliMixin):
    write_column: str
    mode: t.Literal["error", "append", "overwrite", "ignore"] = "error"

    @staticmethod
    def get_cli_options() -> t.List[click.Option]:
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
        return options


@click.command(name="delta-table")
@click.pass_context
def delta_table_dest(ctx: click.Context, **options):
    if not ctx.parent:
        raise click.ClickException("destination command called without a parent")
    if not ctx.parent.info_name:
        raise click.ClickException("parent command missing info name")
    source_cmd = ctx.parent.info_name.replace("-", "_")
    parent_options: dict = ctx.parent.params if ctx.parent else {}
    conform_click_options(options)
    conform_click_options(parent_options)
    verbose = parent_options.get("verbose", False)
    ingest_log_streaming_init(logging.DEBUG if verbose else logging.INFO)
    log_options(parent_options, verbose=verbose)
    log_options(options, verbose=verbose)
    try:
        orchestrate_runner(
            source_cmd=source_cmd,
            writer_type="delta_table",
            parent_options=parent_options,
            options=options,
            validate=[DeltaTableCliWriteConfig],
        )
    except Exception as e:
        logger.error(e, exc_info=True)
        raise click.ClickException(str(e)) from e


def get_dest_cmd() -> click.Command:
    cmd = delta_table_dest
    DeltaTableCliConfig.add_cli_options(cmd)
    DeltaTableCliWriteConfig.add_cli_options(cmd)
    return cmd


def get_base_src_cmd() -> BaseSrcCmd:
    cmd_cls = BaseSrcCmd(cmd_name="delta-table", cli_config=DeltaTableCliConfig)
    return cmd_cls
