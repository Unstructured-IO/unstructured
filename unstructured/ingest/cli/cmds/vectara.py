import typing as t
from dataclasses import dataclass

import click

from unstructured.ingest.cli.interfaces import CliConfig
from unstructured.ingest.connector.vectara import SimpleVectaraConfig, WriteConfig


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
                envvar="VECTARA_CUSTOMER_ID",
                show_envvar=True,
            ),
            click.Option(
                ["--oauth-client-id"],
                required=True,
                type=str,
                help="Vectara OAuth2 client ID.",
                envvar="VECTARA_OAUTH_CLIENT_ID",
                show_envvar=True,
            ),
            click.Option(
                ["--oauth-secret"],
                required=True,
                type=str,
                help="Vectara OAuth2 secret.",
                envvar="VECTARA_OAUTH_SECRET",
                show_envvar=True,
            ),
            click.Option(
                ["--corpus-name"],
                required=False,
                type=str,
                default=None,
                help="The Vectara corpus-name.",
            ),
            click.Option(
                ["--token-url"],
                required=False,
                default="https://vectara-prod-{}.auth.us-west-2.amazoncognito.com/oauth2/token",
                type=str,
                help="The Vectara endpoint for token refresh. Needs curly brackets for customer_id",
            ),
        ]
        return options


def get_base_dest_cmd():
    from unstructured.ingest.cli.base.dest import BaseDestCmd

    cmd_cls = BaseDestCmd(
        cmd_name="vectara",
        cli_config=VectaraCliWriteConfig,
        additional_cli_options=[],
        write_config=WriteConfig,
    )
    return cmd_cls
