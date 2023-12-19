import typing as t
from dataclasses import dataclass

import click

from unstructured.ingest.cli.interfaces import CliConfig, Dict
from unstructured.ingest.connector.weaviate import SimpleWeaviateConfig, WeaviateWriteConfig

CMD_NAME = "weaviate"


@dataclass
class WeaviateCliConfig(SimpleWeaviateConfig, CliConfig):
    @staticmethod
    def get_cli_options() -> t.List[click.Option]:
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
                ["--auth-keys"],
                required=False,
                type=Dict(),
                help=(
                    "String representing a JSON-like dict with key,value containing "
                    "the required parameters to create an authentication object. "
                    'example: \'{"api_key":"123abc!"}\' '
                    "The connector resolves the authentication object from the parameters. "
                    "See https://weaviate.io/developers/weaviate/client-libraries/python_v3"
                    "#api-key-authentication "
                    "for more information."
                ),
            ),
        ]
        return options


@dataclass
class WeaviateCliWriteConfig(WeaviateWriteConfig, CliConfig):
    @staticmethod
    def get_cli_options() -> t.List[click.Option]:
        options = [
            click.Option(
                ["--batch-size"],
                default=100,
                type=int,
                help="Number of records per batch",
            )
        ]
        return options


def get_base_dest_cmd():
    from unstructured.ingest.cli.base.dest import BaseDestCmd

    cmd_cls = BaseDestCmd(
        cmd_name=CMD_NAME,
        cli_config=WeaviateCliConfig,
        additional_cli_options=[WeaviateCliWriteConfig],
        write_config=WeaviateWriteConfig,
    )
    return cmd_cls
