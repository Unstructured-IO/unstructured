import typing as t
from dataclasses import dataclass

import click

from unstructured.ingest.cli.interfaces import CliConfig
from unstructured.ingest.connector.sql import SimpleSqlConfig, SqlWriteConfig

SQL_DRIVERS = {"postgresql", "sqlite"}


@dataclass
class SqlCliConfig(SimpleSqlConfig, CliConfig):
    @staticmethod
    def get_cli_options() -> t.List[click.Option]:
        options = [
            click.Option(
                ["--db_type"],
                required=True,
                type=click.Choice(SQL_DRIVERS),
                help="Type of the database backend",
            ),
            click.Option(
                ["--username"],
                default=None,
                type=str,
                help="DB username",
            ),
            click.Option(
                ["--password"],
                default=None,
                type=str,
                help="DB password",
            ),
            click.Option(
                ["--host"],
                default=None,
                type=str,
                help="DB host",
            ),
            click.Option(
                ["--port"],
                default=None,
                type=int,
                help="DB host connection port",
            ),
            click.Option(
                ["--database"],
                default=None,
                type=str,
                help="Database name. For sqlite databases, this is the path to the .db file.",
            ),
        ]
        return options


@dataclass
class SqlCliWriteConfig(SqlWriteConfig, CliConfig):
    @staticmethod
    def get_cli_options() -> t.List[click.Option]:
        options = [
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


def get_base_dest_cmd():
    from unstructured.ingest.cli.base.dest import BaseDestCmd

    cmd_cls = BaseDestCmd(
        cmd_name="sql",
        cli_config=SqlCliConfig,
        additional_cli_options=[SqlCliWriteConfig],
        write_config=SqlWriteConfig,
    )
    return cmd_cls
