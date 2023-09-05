import logging
import typing as t
from dataclasses import dataclass

import click

from unstructured.ingest.cli.cmds.utils import Group
from unstructured.ingest.cli.common import (
    log_options,
)
from unstructured.ingest.cli.interfaces import (
    CliMixin,
    CliPartitionConfig,
    CliReadConfig,
)
from unstructured.ingest.interfaces2 import BaseConfig
from unstructured.ingest.logger import ingest_log_streaming_init, logger
from unstructured.ingest.runner import biomed as biomed_fn


@dataclass
class BiomedCliConfigs(BaseConfig, CliMixin):
    api_id: t.Optional[str] = None
    api_from: t.Optional[str] = None
    api_until: t.Optional[str] = None
    decay: float = 0.3
    path: t.Optional[str] = None
    max_request_time: int = 45
    max_retries: int = 1

    @staticmethod
    def add_cli_options(cmd: click.Command) -> None:
        options = [
            click.Option(
                ["--api-id"],
                default=None,
                help="ID parameter for OA Web Service API.",
            ),
            click.Option(
                ["--api-from"],
                default=None,
                help="From parameter for OA Web Service API.",
            ),
            click.Option(
                ["--api-until"],
                default=None,
                help="Until parameter for OA Web Service API.",
            ),
            click.Option(
                ["--decay"],
                default=0.3,
                help="(In float) Factor to multiply the delay between retries.",
            ),
            click.Option(
                ["--path"],
                default=None,
                help="PMC Open Access FTP Directory Path.",
            ),
            click.Option(
                ["--max-request-time"],
                default=45,
                help="(In seconds) Max request time to OA Web Service API.",
            ),
            click.Option(
                ["--max-retries"],
                default=1,
                help="Max requests to OA Web Service API.",
            ),
        ]
        cmd.params.extend(options)


@click.group(name="biomed", invoke_without_command=True, cls=Group)
@click.pass_context
def biomed_source(ctx: click.Context, **options):
    if ctx.invoked_subcommand:
        return

    # Click sets all multiple fields as tuple, this needs to be updated to list
    for k, v in options.items():
        if isinstance(v, tuple):
            options[k] = list(v)
    verbose = options.get("verbose", False)
    ingest_log_streaming_init(logging.DEBUG if verbose else logging.INFO)
    log_options(options, verbose=verbose)
    try:
        # run_init_checks(**options)
        read_configs = CliReadConfig.from_dict(options)
        partition_configs = CliPartitionConfig.from_dict(options)
        # Run for schema validation
        BiomedCliConfigs.from_dict(options)
        biomed_fn(read_config=read_configs, partition_configs=partition_configs, **options)
    except Exception as e:
        logger.error(e, exc_info=True)
        raise click.ClickException(str(e)) from e


def get_source_cmd() -> click.Group:
    cmd = biomed_source
    BiomedCliConfigs.add_cli_options(cmd)

    # Common CLI configs
    CliReadConfig.add_cli_options(cmd)
    CliPartitionConfig.add_cli_options(cmd)
    cmd.params.append(click.Option(["-v", "--verbose"], is_flag=True, default=False))
    return cmd
