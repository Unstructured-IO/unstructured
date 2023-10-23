import logging
import typing as t
from dataclasses import dataclass

import click

from unstructured.ingest.cli.common import (
    log_options,
)
from unstructured.ingest.cli.interfaces import (
    CliMixin,
    CliRecursiveConfig,
    DelimitedString,
)
from unstructured.ingest.cli.utils import Group, add_options, conform_click_options, extract_configs
from unstructured.ingest.interfaces import BaseConfig
from unstructured.ingest.logger import ingest_log_streaming_init, logger
from unstructured.ingest.runner import OutlookRunner


@dataclass
class OutlookCliConfig(BaseConfig, CliMixin):
    client_id: str
    user_email: str
    tenant: t.Optional[str] = "common"
    outlook_folders: t.Optional[t.List[str]] = None
    client_cred: t.Optional[str] = None
    authority_url: t.Optional[str] = "https://login.microsoftonline.com"

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


@click.group(name="outlook", invoke_without_command=True, cls=Group)
@click.pass_context
def outlook_source(ctx: click.Context, **options):
    if ctx.invoked_subcommand:
        return

    conform_click_options(options)
    verbose = options.get("verbose", False)
    ingest_log_streaming_init(logging.DEBUG if verbose else logging.INFO)
    log_options(options, verbose=verbose)
    try:
        configs = extract_configs(options, validate=([OutlookCliConfig]))
        runner = OutlookRunner(
            **configs,  # type: ignore
        )
        runner.run(**options)
    except Exception as e:
        logger.error(e, exc_info=True)
        raise click.ClickException(str(e)) from e


def get_source_cmd() -> click.Group:
    cmd = outlook_source
    add_options(cmd, extras=[OutlookCliConfig, CliRecursiveConfig])
    return cmd
