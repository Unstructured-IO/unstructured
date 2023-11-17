import typing as t
from dataclasses import dataclass

import click

from unstructured.ingest.cli.interfaces import CliConfig, DelimitedString, Dict
from unstructured.ingest.connector.mongodb import MongoDBWriteConfig, SimpleMongoDBStorageConfig

CMD_NAME = "mongodb"


@dataclass
class MongoDBCliConfig(SimpleMongoDBStorageConfig, CliConfig):
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
                ["--client-params"],
                type=Dict(),
                help="additional parameters to use when creating mongo client",
            ),
        ]
        return options


@dataclass
class MongoDBCliWriteConfig(MongoDBWriteConfig, CliConfig):
    @staticmethod
    def get_cli_options() -> t.List[click.Option]:
        options = [
            click.Option(
                ["--database"], type=str, required=True, help="database name to connect to"
            ),
            click.Option(
                ["--collection"], required=True, type=str, help="collection name to connect to"
            ),
        ]
        return options


def get_base_dest_cmd():
    from unstructured.ingest.cli.base.dest import BaseDestCmd

    cmd_cls = BaseDestCmd(
        cmd_name=CMD_NAME,
        cli_config=MongoDBCliConfig,
        additional_cli_options=[MongoDBCliWriteConfig],
    )
    return cmd_cls
