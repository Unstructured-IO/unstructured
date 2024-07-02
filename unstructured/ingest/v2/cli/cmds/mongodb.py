from dataclasses import dataclass

import click

from unstructured.ingest.v2.cli.base import DestCmd
from unstructured.ingest.v2.cli.interfaces import CliConfig
from unstructured.ingest.v2.processes.connectors.mongodb import CONNECTOR_TYPE


@dataclass
class MongoDBCliConnectionConfig(CliConfig):
    @staticmethod
    def get_cli_options() -> list[click.Option]:
        options = [
            click.Option(
                ["--uri"],
                help="URI to user when connecting",
            ),
            click.Option(
                ["--host"],
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
class MongoDBCliUploaderConfig(CliConfig):
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
class MongoDBCliUploadStagerConfig(CliConfig):
    @staticmethod
    def get_cli_options() -> list[click.Option]:
        return []


mongodb_dest_cmd = DestCmd(
    cmd_name=CONNECTOR_TYPE,
    connection_config=MongoDBCliConnectionConfig,
    uploader_config=MongoDBCliUploaderConfig,
    upload_stager_config=MongoDBCliUploadStagerConfig,
)
