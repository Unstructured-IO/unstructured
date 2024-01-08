import typing as t
from dataclasses import dataclass

import click

from unstructured.ingest.cli.base.src import BaseSrcCmd
from unstructured.ingest.cli.interfaces import (
    CliConfig,
    CliRecursiveConfig,
    DelimitedString,
)
from unstructured.ingest.connector.salesforce import SimpleSalesforceConfig


@dataclass
class SalesforceCliConfig(SimpleSalesforceConfig, CliConfig):
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
                ["--private-key"],
                required=True,
                type=str,
                help="Path to the private key or its contents for the Salesforce JWT auth. "
                "Key file is usually named server.key.",
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
