from dataclasses import dataclass

import click

from unstructured.ingest.v2.cli.base import DestCmd
from unstructured.ingest.v2.cli.interfaces import CliConfig
from unstructured.ingest.v2.cli.utils import DelimitedString
from unstructured.ingest.v2.processes.connectors.weaviate import CONNECTOR_TYPE


@dataclass
class WeaviateCliConnectionConfig(CliConfig):
    @staticmethod
    def get_cli_options() -> list[click.Option]:
        options = [
            click.Option(
                ["--host-url"],
                required=True,
                help="Weaviate instance url",
            ),
            click.Option(
                ["--class-name"],
                default=None,
                type=str,
                help="Name of the class to push the records into, e.g: Pdf-elements",
            ),
            click.Option(
                ["--access-token"], default=None, type=str, help="Used to create the bearer token."
            ),
            click.Option(
                ["--refresh-token"],
                default=None,
                type=str,
                help="Will tie this value to the bearer token. If not provided, "
                "the authentication will expire once the lifetime of the access token is up.",
            ),
            click.Option(
                ["--api-key"],
                default=None,
                type=str,
            ),
            click.Option(
                ["--client-secret"],
                default=None,
                type=str,
            ),
            click.Option(
                ["--scope"],
                default=None,
                type=DelimitedString(),
            ),
            click.Option(
                ["--username"],
                default=None,
                type=str,
            ),
            click.Option(
                ["--password"],
                default=None,
                type=str,
            ),
            click.Option(
                ["--anonymous"],
                is_flag=True,
                default=False,
                type=bool,
                help="if set, all auth values will be ignored",
            ),
        ]
        return options


@dataclass
class WeaviateCliUploaderConfig(CliConfig):
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
class WeaviateCliUploadStagerConfig(CliConfig):
    @staticmethod
    def get_cli_options() -> list[click.Option]:
        return []


weaviate_dest_cmd = DestCmd(
    cmd_name=CONNECTOR_TYPE,
    connection_config=WeaviateCliConnectionConfig,
    uploader_config=WeaviateCliUploaderConfig,
    upload_stager_config=WeaviateCliUploadStagerConfig,
)
