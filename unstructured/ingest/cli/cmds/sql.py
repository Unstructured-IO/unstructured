import typing as t
from dataclasses import dataclass

import click

from unstructured.ingest.cli.interfaces import CliMixin, Dict
from unstructured.ingest.interfaces import BaseConfig

CMD_NAME = "sql"


@dataclass
class SqlCliWriteConfig(BaseConfig, CliMixin):
    db_name: str
    username: str
    password: str
    host: str
    database: str
    port: int = 5432

    @staticmethod
    def get_cli_options() -> t.List[click.Option]:
        options = [
            click.Option(
                ["--db-name"],
                required=True,
                default="postgres",
                help="SQL Database type",
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
        ]
        return options


def get_base_dest_cmd():
    from unstructured.ingest.cli.base.dest import BaseDestCmd

    cmd_cls = BaseDestCmd(
        cmd_name=CMD_NAME,
        cli_config=SqlCliWriteConfig,
    )
    return cmd_cls
