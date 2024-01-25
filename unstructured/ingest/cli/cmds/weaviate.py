import typing as t
from dataclasses import dataclass

import click

from unstructured.ingest.cli.interfaces import CliConfig, DelimitedString
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
