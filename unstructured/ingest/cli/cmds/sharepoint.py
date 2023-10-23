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
)
from unstructured.ingest.cli.utils import Group, add_options, conform_click_options, extract_configs
from unstructured.ingest.interfaces import BaseConfig
from unstructured.ingest.logger import ingest_log_streaming_init, logger
from unstructured.ingest.runner import SharePointRunner


@dataclass
class SharepointCliConfig(BaseConfig, CliMixin):
    client_id: t.Optional[str] = None
    client_cred: t.Optional[str] = None
    site: t.Optional[str] = None
    path: str = "Shared Documents"
    files_only: bool = False

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
        configs = extract_configs(data=options, validate=[SharepointCliConfig])
        sharepoint_runner = SharePointRunner(
            **configs,  # type: ignore
        )
        sharepoint_runner.run(**options)
    except Exception as e:
        logger.error(e, exc_info=True)
        raise click.ClickException(str(e)) from e


def get_source_cmd() -> click.Group:
    cmd = sharepoint_source
    add_options(cmd, extras=[SharepointCliConfig, CliRecursiveConfig])
    return cmd
