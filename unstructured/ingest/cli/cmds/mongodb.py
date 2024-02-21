import typing as t
from dataclasses import dataclass

import click

from unstructured.ingest.cli.base.src import BaseSrcCmd
from unstructured.ingest.cli.interfaces import CliConfig, DelimitedString
from unstructured.ingest.connector.mongodb import SimpleMongoDBConfig
from unstructured.ingest.interfaces import WriteConfig

CMD_NAME = "mongodb"


@dataclass
class MongoDBCliConfig(SimpleMongoDBConfig, CliConfig):
    @staticmethod
    def get_cli_options() -> t.List[click.Option]:
        options = [
            click.Option(
                ["--uri"],
                help="URI to user when connecting",
            ),
            click.Option(
                ["--host"],
                type=DelimitedString(),
                help="hostname or IP address or Unix domain socket path of a single mongod or "
                "mongos instance to connect to, or a list of hostnames",
            ),
            click.Option(["--port"], type=int, default=27017),
            click.Option(
                ["--database"], type=str, required=True, help="database name to connect to"
            ),
            click.Option(
                ["--collection"], required=True, type=str, help="collection name to connect to"
            ),
        ]
        return options


@dataclass
class MongoDBReadConfig(SimpleMongoDBConfig, CliConfig):
    @staticmethod
    def get_cli_options() -> t.List[click.Option]:
        options = [
            click.Option(
                ["--batch-size"],
                default=100,
                type=click.IntRange(0),
                help="how many records to read at a time per process",
            ),
        ]
        return options


def get_base_src_cmd() -> BaseSrcCmd:
    cmd_cls = BaseSrcCmd(
        cmd_name=CMD_NAME,
        cli_config=MongoDBCliConfig,
        additional_cli_options=[MongoDBReadConfig],
    )
    return cmd_cls


def get_base_dest_cmd():
    from unstructured.ingest.cli.base.dest import BaseDestCmd

    cmd_cls = BaseDestCmd(
        cmd_name=CMD_NAME,
        cli_config=MongoDBCliConfig,
        write_config=WriteConfig,
    )
    return cmd_cls
