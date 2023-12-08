import typing as t
from dataclasses import dataclass

import click

from unstructured.ingest.cli.interfaces import (
    CliConfig,
)
from unstructured.ingest.connector.chroma import ChromaWriteConfig, SimpleChromaConfig


@dataclass
class ChromaCliConfig(SimpleChromaConfig, CliConfig):
    @staticmethod
    def get_cli_options() -> t.List[click.Option]:
        options = [
            click.Option(
                ["--db-path"],
                required=True,
                type=str,
                help="Location where Chroma is persisted.",
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
class ChromaCliWriteConfig(ChromaWriteConfig, CliConfig):
    @staticmethod
    def get_cli_options() -> t.List[click.Option]:
        options = [
            click.Option(
                ["--batch-size"],
                default=100,
                type=int,
                help="Number of records per batch",
            ),
        ]
        return options


def get_base_dest_cmd():
    from unstructured.ingest.cli.base.dest import BaseDestCmd

    cmd_cls = BaseDestCmd(
        cmd_name="chroma",
        cli_config=ChromaCliConfig,
        additional_cli_options=[ChromaCliWriteConfig],
        addition_configs={
            "connector_config": SimpleChromaConfig,
            "write_config": ChromaWriteConfig,
        },
    )
    return cmd_cls
