import typing as t
from dataclasses import dataclass

import click

from unstructured.ingest.cli.base.src import BaseSrcCmd
from unstructured.ingest.cli.interfaces import (
    CliConfig,
    CliRecursiveConfig,
    DelimitedString,
)
from unstructured.ingest.connector.outlook import SimpleOutlookConfig


@dataclass
class OutlookCliConfig(SimpleOutlookConfig, CliConfig):
    @staticmethod
    def get_cli_options() -> t.List[click.Option]:
        options = [
            click.Option(
                ["--client-id"],
                required=True,
                type=str,
                help="Microsoft app client ID",
            ),
            click.Option(
                ["--user-email"],
                required=True,
                type=str,
                help="Outlook email to download messages from.",
            ),
            click.Option(
                ["--tenant"],
                default="common",
                help="ID or domain name associated with your Azure AD instance",
            ),
            click.Option(
                ["--outlook-folders"],
                default=None,
                type=DelimitedString(),
                help="Folders to download email messages from. "
                "Do not specify subfolders. Use quotes if spaces in folder names.",
            ),
            click.Option(
                ["--client-cred"],
                default=None,
                type=str,
                help="Microsoft App client secret",
            ),
            click.Option(
                ["--authority-url"],
                default="https://login.microsoftonline.com",
                type=str,
                help="Authentication token provider for Microsoft apps, default is "
                "https://login.microsoftonline.com",
            ),
        ]
        return options


def get_base_src_cmd() -> BaseSrcCmd:
    cmd_cls = BaseSrcCmd(
        cmd_name="outlook",
        cli_config=OutlookCliConfig,
        additional_cli_options=[CliRecursiveConfig],
    )
    return cmd_cls
