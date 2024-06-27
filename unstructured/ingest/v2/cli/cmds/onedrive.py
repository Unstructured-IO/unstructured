from dataclasses import dataclass

import click

from unstructured.ingest.v2.cli.base import SrcCmd
from unstructured.ingest.v2.cli.interfaces import CliConfig
from unstructured.ingest.v2.processes.connectors.onedrive import CONNECTOR_TYPE


@dataclass
class OnedriveCliConnectionConfig(CliConfig):
    @staticmethod
    def get_cli_options() -> list[click.Option]:
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
                ["--authority-url"],
                default="https://login.microsoftonline.com",
                type=str,
                help="Authentication token provider for Microsoft apps, default is "
                "https://login.microsoftonline.com",
            ),
        ]
        return options


@dataclass
class OnedriveCliIndexerConfig(CliConfig):
    @staticmethod
    def get_cli_options() -> list[click.Option]:
        options = [
            click.Option(
                ["--path"],
                default=None,
                type=str,
                help="Folder to start parsing files from.",
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
class OnedriveCliDownloadConfig(CliConfig):
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


onedrive_drive_src_cmd = SrcCmd(
    cmd_name=CONNECTOR_TYPE,
    connection_config=OnedriveCliConnectionConfig,
    indexer_config=OnedriveCliIndexerConfig,
    downloader_config=OnedriveCliDownloadConfig,
)
