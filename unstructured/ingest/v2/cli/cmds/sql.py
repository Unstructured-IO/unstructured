from dataclasses import dataclass

import click

from unstructured.ingest.v2.cli.base import DestCmd
from unstructured.ingest.v2.cli.interfaces import CliConfig
from unstructured.ingest.v2.processes.connectors.sql import CONNECTOR_TYPE

SQL_DRIVERS = {"postgresql", "sqlite"}


@dataclass
class SQLCliConnectionConfig(CliConfig):
    @staticmethod
    def get_cli_options() -> list[click.Option]:
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


@dataclass
class SQLCliUploaderConfig(CliConfig):
    @staticmethod
    def get_cli_options() -> list[click.Option]:
        options = [
            click.Option(
                ["--batch-size"],
                default=100,
                type=int,
                help="Number of records per batch",
            )
        ]
        return options


@dataclass
class SQLCliUploadStagerConfig(CliConfig):
    @staticmethod
    def get_cli_options() -> list[click.Option]:
        return []


sql_dest_cmd = DestCmd(
    cmd_name=CONNECTOR_TYPE,
    connection_config=SQLCliConnectionConfig,
    uploader_config=SQLCliUploaderConfig,
    upload_stager_config=SQLCliUploadStagerConfig,
)
