import typing as t
from dataclasses import dataclass

import click

from unstructured.ingest.cli.interfaces import (
    CliMixin,
)
from unstructured.ingest.interfaces import BaseConfig


@dataclass
class ChromaCliWriteConfig(BaseConfig, CliMixin):
    api_key: str
    index_name: str

    @staticmethod
    def get_cli_options() -> t.List[click.Option]:
        options = [
            click.Option(
                ["--client"], #### Could be endpoint?
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


def get_base_dest_cmd():
    from unstructured.ingest.cli.base.dest import BaseDestCmd

    cmd_cls = BaseDestCmd(
        cmd_name="chroma",
        cli_config=ChromaCliWriteConfig,
    )
    return cmd_cls