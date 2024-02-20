import typing as t
from dataclasses import dataclass

import click

from unstructured.ingest.cli.interfaces import CliConfig, Dict
from unstructured.ingest.connector.astra import AstraDBWriteConfig, SimpleAstraDBConfig


@dataclass
class AstraDBCliConfig(SimpleAstraDBConfig, CliConfig):
    @staticmethod
    def get_cli_options() -> t.List[click.Option]:
        options = [
            click.Option(
                ["--token"],
                required=True,
                type=str,
                help="Astra DB Token with access to the database.",
            ),
            click.Option(
                ["--api-endpoint"],
                required=True,
                type=str,
                help="The API endpoint for the Astra DB.",
            ),
            click.Option(
                ["--collection-name"],
                required=False,
                type=str,
                help="The name of the Astra DB collection to write into. Note that the collection name must only include letters, numbers, and underscores.",
            ),
            click.Option(
                ["--embedding-dimension"],
                default=384,
                type=int,
                help="The dimensionality of the embeddings",
            ),
        ]
        return options


@dataclass
class AstraDBCliWriteConfig(AstraDBWriteConfig, CliConfig):
    @staticmethod
    def get_cli_options() -> t.List[click.Option]:
        options = [
            click.Option(
                ["--batch-size"],
                default=20,
                type=int,
                help="Number of records per batch",
            ),
        ]
        return options


def get_base_dest_cmd():
    from unstructured.ingest.cli.base.dest import BaseDestCmd

    cmd_cls = BaseDestCmd(
        cmd_name="astra",
        cli_config=AstraDBCliConfig,
        additional_cli_options=[AstraDBCliWriteConfig],
        write_config=AstraDBWriteConfig,
    )
    return cmd_cls
