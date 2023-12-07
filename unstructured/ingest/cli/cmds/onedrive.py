import typing as t
from dataclasses import dataclass

import click

from unstructured.ingest.cli.base.src import BaseSrcCmd
from unstructured.ingest.cli.interfaces import (
    CliConfig,
    CliRecursiveConfig,
)
from unstructured.ingest.connector.onedrive import SimpleOneDriveConfig


@dataclass
class OnedriveCliConfig(SimpleOneDriveConfig, CliConfig):
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
                ["--client-cred"],
                required=True,
                type=str,
                help="Microsoft App client secret",
            ),
            click.Option(
                ["--user-pname"],
                required=True,
                type=str,
                help="User principal name, usually is your Azure AD email.",
            ),
            click.Option(
                ["--tenant"],
                default="common",
                type=str,
                help="ID or domain name associated with your Azure AD instance",
            ),
            click.Option(
                ["--path"],
                default=None,
                type=str,
                help="Folder to start parsing files from.",
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
        cmd_name="onedrive",
        cli_config=OnedriveCliConfig,
        additional_cli_options=[CliRecursiveConfig],
    )
    return cmd_cls
