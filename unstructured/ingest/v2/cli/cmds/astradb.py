from dataclasses import dataclass

import click

from unstructured.ingest.v2.cli.base import DestCmd
from unstructured.ingest.v2.cli.interfaces import CliConfig
from unstructured.ingest.v2.cli.utils import Dict
from unstructured.ingest.v2.processes.connectors.astradb import CONNECTOR_TYPE


@dataclass
class AstraDBCliConnectionConfig(CliConfig):
    @staticmethod
    def get_cli_options() -> list[click.Option]:
        options = [
            click.Option(
                ["--token"],
                required=True,
                type=str,
                help="Astra DB Token with access to the database.",
                envvar="ASTRA_DB_APPLICATION_TOKEN",
                show_envvar=True,
            ),
            click.Option(
                ["--api-endpoint"],
                required=True,
                type=str,
                help="The API endpoint for the Astra DB.",
                envvar="ASTRA_DB_API_ENDPOINT",
                show_envvar=True,
            ),
        ]
        return options


@dataclass
class AstraDBCliUploaderConfig(CliConfig):
    @staticmethod
    def get_cli_options() -> list[click.Option]:
        options = [
            click.Option(
                ["--collection-name"],
                required=False,
                type=str,
                help="The name of the Astra DB collection. "
                "Note that the collection name must only include letters, "
                "numbers, and underscores.",
            ),
            click.Option(
                ["--embedding-dimension"],
                required=True,
                default=384,
                type=int,
                help="The dimensionality of the embeddings",
            ),
            click.Option(
                ["--namespace"],
                required=False,
                default=None,
                type=str,
                help="The Astra DB connection namespace.",
            ),
            click.Option(
                ["--requested-indexing-policy"],
                required=False,
                default=None,
                type=Dict(),
                help="The indexing policy to use for the collection."
                'example: \'{"deny": ["metadata"]}\' ',
            ),
            click.Option(
                ["--batch-size"],
                default=20,
                type=int,
                help="Number of records per batch",
            ),
        ]
        return options


astradb_dest_cmd = DestCmd(
    cmd_name=CONNECTOR_TYPE,
    connection_config=AstraDBCliConnectionConfig,
    uploader_config=AstraDBCliUploaderConfig,
)
