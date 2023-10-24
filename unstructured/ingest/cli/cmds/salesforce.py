import typing as t
from dataclasses import dataclass

import click

from unstructured.ingest.cli.base.src import BaseSrcCmd
from unstructured.ingest.cli.interfaces import (
    CliMixin,
    CliRecursiveConfig,
    DelimitedString,
)
from unstructured.ingest.interfaces import BaseConfig


@dataclass
class SalesforceCliConfig(BaseConfig, CliMixin):
    username: str
    consumer_key: str
    private_key_path: str
    categories: t.List[str]

    @staticmethod
    def get_cli_options() -> t.List[click.Option]:
        possible_categories = ["Account", "Case", "Campaign", "EmailMessage", "Lead"]
        options = [
            click.Option(
                ["--username"],
                required=True,
                type=str,
                help="Salesforce username usually looks like an email.",
            ),
            click.Option(
                ["--consumer-key"],
                required=True,
                type=str,
                help="For the Salesforce JWT auth. Found in Consumer Details.",
            ),
            click.Option(
                ["--private-key-path"],
                required=True,
                type=click.Path(file_okay=True, exists=True, dir_okay=False),
                help="Path to the private key for the Salesforce JWT auth. "
                "Usually named server.key.",
            ),
            click.Option(
                ["--categories"],
                default=None,
                required=True,
                type=DelimitedString(choices=possible_categories),
                help="Comma-delimited salesforce categories to download. "
                "Currently only {}.".format(", ".join(possible_categories)),
            ),
        ]
        return options


def get_base_src_cmd() -> BaseSrcCmd:
    cmd_cls = BaseSrcCmd(
        cmd_name="salesforce",
        cli_config=SalesforceCliConfig,
        additional_cli_options=[CliRecursiveConfig],
    )
    return cmd_cls
