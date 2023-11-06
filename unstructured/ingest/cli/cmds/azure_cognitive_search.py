import typing as t
from dataclasses import dataclass

import click

from unstructured.ingest.cli.interfaces import (
    CliConfig,
)


@dataclass
class AzureCognitiveSearchCliWriteConfig(CliConfig):
    key: str
    endpoint: str
    index: str

    @staticmethod
    def get_cli_options() -> t.List[click.Option]:
        options = [
            click.Option(
                ["--key"],
                required=True,
                type=str,
                help="Key credential used for authenticating to an Azure service.",
                envvar="AZURE_SEARCH_API_KEY",
                show_envvar=True,
            ),
            click.Option(
                ["--endpoint"],
                required=True,
                type=str,
                help="The URL endpoint of an Azure search service. "
                "In the form of https://{{service_name}}.search.windows.net",
                envvar="AZURE_SEARCH_ENDPOINT",
                show_envvar=True,
            ),
            click.Option(
                ["--index"],
                required=True,
                type=str,
                help="The name of the index to connect to",
            ),
        ]
        return options


def get_base_dest_cmd():
    from unstructured.ingest.cli.base.dest import BaseDestCmd

    cmd_cls = BaseDestCmd(
        cmd_name="azure-cognitive-search",
        cli_config=AzureCognitiveSearchCliWriteConfig,
    )
    return cmd_cls
