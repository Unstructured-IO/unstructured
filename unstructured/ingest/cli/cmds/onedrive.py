import logging
import typing as t
from dataclasses import dataclass

import click

from unstructured.ingest.cli.cmds.utils import Group, conform_click_options
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
from unstructured.ingest.runner import onedrive as onedrive_fn


@dataclass
class OnedriveCliConfig(BaseConfig, CliMixin):
    client_id: str
    client_cred: str
    user_pname: str
    tenant: str = "common"
    path: t.Optional[str] = None
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
        cmd.params.extend(options)


@click.group(name="onedrive", invoke_without_command=True, cls=Group)
@click.pass_context
def onedrive_source(ctx: click.Context, **options):
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
        OnedriveCliConfig.from_dict(options)
        onedrive_fn(read_config=read_config, partition_config=partition_config, **options)
    except Exception as e:
        logger.error(e, exc_info=True)
        raise click.ClickException(str(e)) from e


def get_source_cmd() -> click.Group:
    cmd = onedrive_source
    OnedriveCliConfig.add_cli_options(cmd)
    CliRecursiveConfig.add_cli_options(cmd)

    # Common CLI configs
    CliReadConfig.add_cli_options(cmd)
    CliPartitionConfig.add_cli_options(cmd)
    cmd.params.append(click.Option(["-v", "--verbose"], is_flag=True, default=False))
    return cmd
