import typing as t
from dataclasses import dataclass

import click

from unstructured.ingest.cli.interfaces import CliConfig
from unstructured.ingest.connector.vectara import SimpleVectaraConfig, VectaraWriteConfig


@dataclass
class VectaraCliWriteConfig(SimpleVectaraConfig, CliConfig):
    @staticmethod
    def get_cli_options() -> t.List[click.Option]:
        options = [
            click.Option(
                ["--customer-id"],
                required=True,
                type=str,
                help="The Vectara customer-id.",
            ),
            click.Option(
                ["--oauth-client-id"],
                required=True,
                type=str,
                help="Vectara OAuth2 client ID.",
            ),
            click.Option(
                ["--oauth-secret"],
                required=True,
                type=str,
                help="Vectara OAuth2 secret.",
            ),
            click.Option(
                ["--corpus-name"],
                required=False,
                default="vectara-unstructured",
                type=str,
                help="The Vectara corpus-name.",
            ),
        ]
        return options


def get_base_dest_cmd():
    from unstructured.ingest.cli.base.dest import BaseDestCmd

    cmd_cls = BaseDestCmd(
        cmd_name="vectara",
        cli_config=VectaraCliWriteConfig,
        additional_cli_options=[],
        write_config=VectaraWriteConfig,
    )
    return cmd_cls
