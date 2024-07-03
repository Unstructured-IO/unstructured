from dataclasses import dataclass

import click

from unstructured.ingest.v2.cli.base import SrcCmd
from unstructured.ingest.v2.cli.interfaces import CliConfig
from unstructured.ingest.v2.processes.connectors.sharepoint import CONNECTOR_TYPE


@dataclass
class SharepointCliConnectionConfig(CliConfig):
    @staticmethod
    def get_cli_options() -> list[click.Option]:
        options = [
            click.Option(
                ["--client-id"],
                default=None,
                type=str,
                help="Sharepoint app client ID",
            ),
            click.Option(
                ["--client-cred"],
                default=None,
                type=str,
                help="Sharepoint app secret",
            ),
            click.Option(
                ["--site"],
                default=None,
                type=str,
                help="Sharepoint site url. Process either base url e.g \
                    https://[tenant].sharepoint.com  or relative sites \
                    https://[tenant].sharepoint.com/sites/<site_name>. \
                    To process all sites within the tenant pass a site url as \
                    https://[tenant]-admin.sharepoint.com.\
                    This requires the app to be registered at a tenant level",
            ),
            click.Option(
                ["--permissions-application-id"],
                type=str,
                help="Microsoft Graph API application id",
            ),
            click.Option(
                ["--permissions-client-cred"],
                type=str,
                help="Microsoft Graph API application credentials",
            ),
            click.Option(
                ["--permissions-tenant"],
                type=str,
                help="e.g https://contoso.onmicrosoft.com to get permissions data within tenant.",
            ),
        ]
        return options


@dataclass
class SharepointCliIndexerConfig(CliConfig):
    @staticmethod
    def get_cli_options() -> list[click.Option]:
        options = [
            click.Option(
                ["--path"],
                default=None,
                type=str,
                help="Path from which to start parsing files. If the connector is to \
                process all sites within the tenant this filter will be applied to \
                all sites document libraries.",
            ),
            click.Option(
                ["--recursive"],
                is_flag=True,
                default=False,
                help="Recursively download files in their respective folders "
                "otherwise stop at the files in provided folder level.",
            ),
            click.Option(
                ["--omit-files"],
                is_flag=True,
                default=False,
                help="Don't process files.",
            ),
            click.Option(
                ["--omit-pages"],
                is_flag=True,
                default=False,
                help="Don't process site pages.",
            ),
        ]
        return options


@dataclass
class SharepointCliDownloadConfig(CliConfig):
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


sharepoint_drive_src_cmd = SrcCmd(
    cmd_name=CONNECTOR_TYPE,
    connection_config=SharepointCliConnectionConfig,
    indexer_config=SharepointCliIndexerConfig,
    downloader_config=SharepointCliDownloadConfig,
)
