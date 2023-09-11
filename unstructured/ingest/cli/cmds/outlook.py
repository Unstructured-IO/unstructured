import logging
import typing as t
from dataclasses import dataclass

import click

from unstructured.ingest.cli.cmds.utils import (
    DelimitedString,
    Group,
    conform_click_options,
)
from unstructured.ingest.cli.common import (
    log_options,
)
from unstructured.ingest.cli.interfaces import (
    CliMixin,
    CliPartitionConfig,
    CliReadConfig,
    CliRecursiveConfig,
)
from unstructured.ingest.interfaces import BaseConfig
from unstructured.ingest.logger import ingest_log_streaming_init, logger
from unstructured.ingest.runner import outlook as outlook_fn


@dataclass
class OutlookCliConfig(BaseConfig, CliMixin):
    client_id: str
    user_email: str
    tenant: t.Optional[str] = "common"
    outlook_folders: t.Optional[t.List[str]] = None
    client_cred: t.Optional[str] = None
    authority_url: t.Optional[str] = "https://login.microsoftonline.com"

    @staticmethod
    def add_cli_options(cmd: click.Command) -> None:
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
        cmd.params.extend(options)


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
        # run_init_checks(**options)
        read_config = CliReadConfig.from_dict(options)
        partition_config = CliPartitionConfig.from_dict(options)
        # Run for schema validation
        OutlookCliConfig.from_dict(options)
        outlook_fn(read_config=read_config, partition_config=partition_config, **options)
    except Exception as e:
        logger.error(e, exc_info=True)
        raise click.ClickException(str(e)) from e


def get_source_cmd() -> click.Group:
    cmd = outlook_source
    OutlookCliConfig.add_cli_options(cmd)
    CliRecursiveConfig.add_cli_options(cmd)

    # Common CLI configs
    CliReadConfig.add_cli_options(cmd)
    CliPartitionConfig.add_cli_options(cmd)
    cmd.params.append(click.Option(["-v", "--verbose"], is_flag=True, default=False))
    return cmd
