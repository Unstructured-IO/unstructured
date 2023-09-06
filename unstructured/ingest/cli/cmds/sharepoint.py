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
from unstructured.ingest.runner import sharepoint as sharepoint_fn


@dataclass
class SharepointCliConfigs(BaseConfig, CliMixin):
    client_id: t.Optional[str] = None
    client_cred: t.Optional[str] = None
    site: t.Optional[str] = None
    path: str = "Shared Documents"

    @staticmethod
    def add_cli_options(cmd: click.Command) -> None:
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
        ]
        cmd.params.extend(options)


@click.group(name="sharepoint", invoke_without_command=True, cls=Group)
@click.pass_context
def sharepoint_source(ctx: click.Context, **options):
    if ctx.invoked_subcommand:
        return

    conform_click_options(options)
    verbose = options.get("verbose", False)
    ingest_log_streaming_init(logging.DEBUG if verbose else logging.INFO)
    log_options(options, verbose=verbose)
    try:
        # run_init_checks(**options)
        read_configs = CliReadConfig.from_dict(options)
        partition_configs = CliPartitionConfig.from_dict(options)
        # Run for schema validation
        SharepointCliConfigs.from_dict(options)
        sharepoint_fn(read_config=read_configs, partition_configs=partition_configs, **options)
    except Exception as e:
        logger.error(e, exc_info=True)
        raise click.ClickException(str(e)) from e


def get_source_cmd() -> click.Group:
    cmd = sharepoint_source
    SharepointCliConfigs.add_cli_options(cmd)
    CliRecursiveConfig.add_cli_options(cmd)

    # Common CLI configs
    CliReadConfig.add_cli_options(cmd)
    CliPartitionConfig.add_cli_options(cmd)
    cmd.params.append(click.Option(["-v", "--verbose"], is_flag=True, default=False))
    return cmd
