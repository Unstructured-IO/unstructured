import typing as t
from dataclasses import dataclass

import click

from unstructured.ingest.cli.interfaces import CliConfig
from unstructured.ingest.connector.sql import SimpleSqlConfig
from unstructured.ingest.interfaces import WriteConfig

SQL_DRIVERS = {"postgresql", "sqlite"}


@dataclass
class SqlCliConfig(SimpleSqlConfig, CliConfig):
    @staticmethod
    def get_cli_options() -> t.List[click.Option]:
        options = [
            click.Option(
                ["--db-type"],
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


def get_base_dest_cmd():
    from unstructured.ingest.cli.base.dest import BaseDestCmd

    cmd_cls = BaseDestCmd(
        cmd_name="sql",
        cli_config=SqlCliConfig,
        write_config=WriteConfig,
    )
    return cmd_cls
