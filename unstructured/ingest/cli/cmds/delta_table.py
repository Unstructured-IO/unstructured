import typing as t
from dataclasses import dataclass

import click

from unstructured.ingest.cli.base.src import BaseSrcCmd
from unstructured.ingest.cli.interfaces import (
    CliConfig,
)
from unstructured.ingest.connector.delta_table import DeltaTableWriteConfig

CMD_NAME = "delta-table"


@dataclass
class DeltaTableCliConfig(CliConfig):
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
class DeltaTableCliWriteConfig(DeltaTableWriteConfig, CliConfig):
    @staticmethod
    def get_cli_options() -> t.List[click.Option]:
        options = [
            click.Option(
                ["--overwrite-schema"],
                is_flag=True,
                default=False,
                help="Flag to overwrite schema of destination table",
            ),
            click.Option(
                ["--drop-empty-cols"],
                is_flag=True,
                default=False,
                help="Flag to drop any columns that have no content",
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


def get_base_src_cmd() -> BaseSrcCmd:
    cmd_cls = BaseSrcCmd(cmd_name=CMD_NAME, cli_config=DeltaTableCliConfig)
    return cmd_cls


def get_base_dest_cmd():
    from unstructured.ingest.cli.base.dest import BaseDestCmd

    cmd_cls = BaseDestCmd(
        cmd_name=CMD_NAME,
        cli_config=DeltaTableCliConfig,
        additional_cli_options=[DeltaTableCliWriteConfig],
    )
    return cmd_cls
