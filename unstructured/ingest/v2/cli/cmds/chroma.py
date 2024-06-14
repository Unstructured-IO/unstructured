from dataclasses import dataclass

import click

from unstructured.ingest.cli.interfaces import Dict
from unstructured.ingest.v2.cli.base import DestCmd
from unstructured.ingest.v2.cli.interfaces import CliConfig
from unstructured.ingest.v2.processes.connectors.chroma import CONNECTOR_TYPE


@dataclass
class ChromaCliConnectionConfig(CliConfig):
    @staticmethod
    def get_cli_options() -> list[click.Option]:
        options = [
            click.Option(
                ["--path"],
                required=False,
                type=str,
                help="Location where Chroma is persisted," "if not connecting via http.",
            ),
            click.Option(
                ["--settings"],
                required=False,
                type=Dict(),
                help="A dictionary of settings to communicate with the chroma server."
                'example: \'{"persist_directory":"./chroma-persist"}\' ',
            ),
            click.Option(
                ["--tenant"],
                required=False,
                default="default_tenant",
                type=str,
                help="The tenant to use for this client. Chroma defaults to 'default_tenant'.",
            ),
            click.Option(
                ["--database"],
                required=False,
                default="default_database",
                type=str,
                help="The database to use for this client."
                "Chroma defaults to 'default_database'.",
            ),
            click.Option(
                ["--host"],
                required=False,
                type=str,
                help="The hostname of the Chroma server.",
            ),
            click.Option(
                ["--port"],
                required=False,
                type=int,
                help="The port of the Chroma server.",
            ),
            click.Option(
                ["--ssl"],
                required=False,
                default=False,
                is_flag=True,
                type=bool,
                help="Whether to use SSL to connect to the Chroma server.",
            ),
            click.Option(
                ["--headers"],
                required=False,
                type=Dict(),
                help="A dictionary of headers to send to the Chroma server."
                'example: \'{"Authorization":"Basic()"}\' ',
            ),
            click.Option(
                ["--collection-name"],
                required=True,
                type=str,
                help="The name of the Chroma collection to write into.",
            ),
        ]
        return options


@dataclass
class ChromaCliUploaderConfig(CliConfig):
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
class ChromaCliUploadStagerConfig(CliConfig):
    @staticmethod
    def get_cli_options() -> list[click.Option]:
        return []


chroma_dest_cmd = DestCmd(
    cmd_name=CONNECTOR_TYPE,
    connection_config=ChromaCliConnectionConfig,
    uploader_config=ChromaCliUploaderConfig,
    upload_stager_config=ChromaCliUploadStagerConfig,
)
