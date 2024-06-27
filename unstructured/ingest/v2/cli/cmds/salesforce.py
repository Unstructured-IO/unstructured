from dataclasses import dataclass

import click

from unstructured.ingest.v2.cli.base import SrcCmd
from unstructured.ingest.v2.cli.interfaces import CliConfig
from unstructured.ingest.v2.cli.utils import DelimitedString, FileOrJson
from unstructured.ingest.v2.processes.connectors.salesforce import CONNECTOR_TYPE


@dataclass
class SalesforceCliConnectionConfig(CliConfig):
    @staticmethod
    def get_cli_options() -> list[click.Option]:
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
        ]
        return options


@dataclass
class SalesforceCliIndexerConfig(CliConfig):
    @staticmethod
    def get_cli_options() -> list[click.Option]:
        possible_categories = ["Account", "Case", "Campaign", "EmailMessage", "Lead"]
        options = [
            click.Option(
                ["--categories"],
                default=None,
                required=True,
                type=DelimitedString(choices=possible_categories),
                help="Comma-delimited salesforce categories to download. "
                "Currently only {}.".format(", ".join(possible_categories)),
            ),
            click.Option(
                ["--recursive"],
                is_flag=True,
                default=False,
                help="Recursively download files in their respective folders "
                "otherwise stop at the files in provided folder level.",
            ),
        ]
        return options


@dataclass
class SalesforceCliDownloadConfig(CliConfig):
    @staticmethod
    def get_cli_options() -> list[click.Option]:
        options = [
            click.Option(
                ["--download-dir"],
                help="Where files are downloaded to, defaults to a location at"
                "`$HOME/.cache/unstructured/ingest/<connector name>/<SHA256>`.",
            ),
        ]
        return options


salesforce_src_cmd = SrcCmd(
    cmd_name=CONNECTOR_TYPE,
    connection_config=SalesforceCliConnectionConfig,
    indexer_config=SalesforceCliIndexerConfig,
    downloader_config=SalesforceCliDownloadConfig,
)
