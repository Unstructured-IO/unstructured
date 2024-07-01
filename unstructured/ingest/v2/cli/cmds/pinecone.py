from dataclasses import dataclass

import click

from unstructured.ingest.v2.cli.base import DestCmd
from unstructured.ingest.v2.cli.interfaces import CliConfig
from unstructured.ingest.v2.processes.connectors.pinecone import CONNECTOR_TYPE


@dataclass
class PineconeCliConnectionConfig(CliConfig):
    @staticmethod
    def get_cli_options() -> list[click.Option]:
        options = [
            click.Option(
                ["--api-key"],
                required=True,
                type=str,
                help="API key for Pinecone.",
            ),
            click.Option(
                ["--index-name"],
                required=True,
                type=str,
                help="Name of the index to connect to. Example: my-index",
            ),
            click.Option(
                ["--environment"],
                required=True,
                type=str,
                help="Environment to connect to. Example: us-east-1",
            ),
        ]
        return options


@dataclass
class PineconeCliUploaderConfig(CliConfig):
    @staticmethod
    def get_cli_options() -> list[click.Option]:
        options = [
            click.Option(
                ["--batch-size"],
                default=100,
                type=int,
                help="Number of records per batch",
            ),
            click.Option(
                ["--num-processes"],
                default=4,
                type=int,
                help="Number of processes to use for uploading",
            ),
        ]
        return options


pinecone_dest_cmd = DestCmd(
    cmd_name=CONNECTOR_TYPE,
    connection_config=PineconeCliConnectionConfig,
    uploader_config=PineconeCliUploaderConfig,
)
