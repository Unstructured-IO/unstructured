import logging
import typing as t
from dataclasses import dataclass

import click

from unstructured.ingest.cli.cmds.utils import Group, conform_click_options, DelimitedString
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
from unstructured.ingest.runner import hubspot as hubspot_fn
from unstructured.ingest.connector.hubspot import HubSpotObjectTypes

OBJECT_TYPES = set([t.value for t in HubSpotObjectTypes])

def validate_object_type(ctx , param, value):
    for obj in value:
        if obj not in OBJECT_TYPES:
            raise click.ClickException(f"Invalid object type: <{obj}>,\
                            must be one of {OBJECT_TYPES}")
    return value

@dataclass
class HubSpotCliConfig(BaseConfig, CliMixin):
    api_token: str
    object_types: t.Optional[t.List[str]] = None

    @staticmethod
    def add_cli_options(cmd: click.Command) -> None:
        options = [
            click.Option(
                ["--api-token"],
                required=True,
                type=str,
                help="Access token to perform operations on Hubspot. \
                    Check \
                    https://developers.hubspot.com/docs/api/private-apps/ \
                    for more info"
            ),
            click.Option(
                ["--object-types"],
                default=None,
                required=False,
                type=DelimitedString(),
                is_flag=False,
                callback=validate_object_type,
                help=f"Object to include in the process. Must be a subset of {','.join(OBJECT_TYPES)}.\
                    If the argument is omitted all objects listed will be processed."
            )]
        cmd.params.extend(options)

@click.group(name="hubspot", invoke_without_command=True, cls=Group)
@click.pass_context
def hubspot_source(ctx: click.Context, **options):
    if ctx.invoked_subcommand:
        return
    conform_click_options(options)
    verbose = options.get("verbose", False)
    ingest_log_streaming_init(logging.DEBUG if verbose else logging.INFO)
    log_options(options, verbose=verbose)
    try:
        read_config = CliReadConfig.from_dict(options)
        partition_config = CliPartitionConfig.from_dict(options)
        # Run for schema validation
        HubSpotCliConfig.from_dict(options)
        hubspot_fn(read_config=read_config, partition_config=partition_config, **options)
    except Exception as e:
        logger.error(e, exc_info=True)
        raise click.ClickException(str(e)) from e


def get_source_cmd() -> click.Group:
    cmd = hubspot_source
    HubSpotCliConfig.add_cli_options(cmd)
    CliRecursiveConfig.add_cli_options(cmd)

    # Common CLI configs
    CliReadConfig.add_cli_options(cmd)
    CliPartitionConfig.add_cli_options(cmd)
    cmd.params.append(click.Option(["-v", "--verbose"], is_flag=True, default=False))
    return cmd