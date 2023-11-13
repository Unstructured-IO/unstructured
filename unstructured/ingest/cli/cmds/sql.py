import typing as t
from dataclasses import dataclass

import click

from unstructured.ingest.cli.interfaces import CliConfig, Dict
from unstructured.ingest.connector.sql.connector import SqlWriteConfig

CMD_NAME = "sql"
SQL_DRIVERS = {"postgresql"}


@dataclass
class SqlCliConfig(CliConfig):
    drivername: str
    username: str
    password: str
    host: str
    database: str
    port: int = 5432

    @staticmethod
    def get_cli_options() -> t.List[click.Option]:
        options = [
            click.Option(
                ["--drivername"],
                default="postgresql",
                type=click.Choice(SQL_DRIVERS),
                help="Name of the database backend",
            ),
            click.Option(
                ["--username"],
                default="postgres",
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
                help="Database name",
            ),
            click.Option(
                ["--database-url"],
                default=None,
                type=str,
                help=(
                    "Database url to be passed to the SQLAlchemy engine. "
                    "If not present, the connector will build the url "
                    "from the other parameters."
                ),
            ),
        ]
        return options


@dataclass
class SqlCliWriteConfig(SqlWriteConfig, CliConfig):
    @staticmethod
    def get_cli_options() -> t.List[click.Option]:
        options = [
            click.Option(
                ["--table-name-mapping"],
                default=None,
                type=Dict(),
                help=("Name of the table(s) mapped to those defined in the example schema."),
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


def get_base_dest_cmd():
    from unstructured.ingest.cli.base.dest import BaseDestCmd

    cmd_cls = BaseDestCmd(
        cmd_name=CMD_NAME, cli_config=SqlCliConfig, additional_cli_options=[SqlCliWriteConfig]
    )
    return cmd_cls
