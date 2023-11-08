import typing as t
from dataclasses import dataclass

import click

from unstructured.ingest.cli.interfaces import (
    CliMixin,
)
from unstructured.ingest.interfaces import BaseConfig


@dataclass
class PineconeCliWriteConfig(BaseConfig, CliMixin):
    api_key: str
    index_name: str
    environment: str
    batch_size: int

    @staticmethod
    def get_cli_options() -> t.List[click.Option]:
        options = [
            click.Option(
                ["--api-key"],
                required=True,
                type=str,
                help="API key used for authenticating to a Pinecone instance.",
                envvar="PINECONE_API_KEY",
                show_envvar=True,
            ),
            click.Option(
                ["--index-name"],
                required=True,
                type=str,
                help="The name of the pinecone index to connect to.",
            ),
            click.Option(
                ["--environment"],
                required=True,
                type=str,
                help="The environment where the index lives. Eg. 'gcp-starter' or 'us-east1-gcp'",
            ),
            click.Option(
                ["--batch-size"],
                default=50,
                type=int,
                help="Number of records per batch",
            ),
        ]
        return options


def get_base_dest_cmd():
    from unstructured.ingest.cli.base.dest import BaseDestCmd

    cmd_cls = BaseDestCmd(
        cmd_name="pinecone",
        cli_config=PineconeCliWriteConfig,
    )
    return cmd_cls
