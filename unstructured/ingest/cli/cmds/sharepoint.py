import typing as t
from dataclasses import dataclass

import click

from unstructured.ingest.cli.base.src import BaseSrcCmd
from unstructured.ingest.cli.interfaces import (
    CliConfig,
    CliRecursiveConfig,
)
from unstructured.ingest.connector.sharepoint import SimpleSharepointConfig


@dataclass
class SharepointCliConfig(SimpleSharepointConfig, CliConfig):
    @staticmethod
    def get_cli_options() -> t.List[click.Option]:
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
                ["--path"],
                default="Shared Documents",
                type=str,
                help="Path from which to start parsing files. If the connector is to \
                process all sites  within the tenant this filter will be applied to \
                all sites document libraries. Default 'Shared Documents'",
            ),
            click.Option(
                ["--files-only"],
                is_flag=True,
                default=False,
                help="Process only files.",
            ),
        ]
        return options


def get_base_src_cmd() -> BaseSrcCmd:
    cmd_cls = BaseSrcCmd(
        cmd_name="sharepoint",
        cli_config=SharepointCliConfig,
        additional_cli_options=[CliRecursiveConfig],
    )
    return cmd_cls
