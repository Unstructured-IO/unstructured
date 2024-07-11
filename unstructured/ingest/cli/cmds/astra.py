import typing as t
from dataclasses import dataclass

import click

from unstructured.ingest.cli.interfaces import CliConfig, Dict
from unstructured.ingest.connector.astra import AstraWriteConfig, SimpleAstraConfig


@dataclass
class AstraCliConfig(SimpleAstraConfig, CliConfig):
    @staticmethod
    def get_cli_options() -> t.List[click.Option]:
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
            click.Option(
                ["--collection-name"],
                required=False,
                type=str,
                help="The name of the Astra DB collection. "
                "Note that the collection name must only include letters, "
                "numbers, and underscores.",
            ),
            click.Option(
                ["--namespace"],
                required=False,
                default=None,
                type=str,
                help="The Astra DB connection namespace.",
            ),
        ]
        return options


@dataclass
class AstraCliWriteConfig(AstraWriteConfig, CliConfig):
    @staticmethod
    def get_cli_options() -> t.List[click.Option]:
        options = [
            click.Option(
                ["--embedding-dimension"],
                required=True,
                default=384,
                type=int,
                help="The dimensionality of the embeddings",
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


def get_base_src_cmd():
    from unstructured.ingest.cli.base.src import BaseSrcCmd

    cmd_cls = BaseSrcCmd(
        cmd_name="astra",
        cli_config=AstraCliConfig,
    )
    return cmd_cls


def get_base_dest_cmd():
    from unstructured.ingest.cli.base.dest import BaseDestCmd

    cmd_cls = BaseDestCmd(
        cmd_name="astra",
        cli_config=AstraCliConfig,
        additional_cli_options=[AstraCliWriteConfig],
        write_config=AstraWriteConfig,
    )
    return cmd_cls
