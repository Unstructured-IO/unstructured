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
    CliRemoteUrlConfig,
)
from unstructured.ingest.interfaces import BaseConfig
from unstructured.ingest.logger import ingest_log_streaming_init, logger
from unstructured.ingest.runner import box as box_fn


@dataclass
class BoxCliConfig(BaseConfig, CliMixin):
    box_app_config: t.Optional[str] = None

    @staticmethod
    def add_cli_options(cmd: click.Command) -> None:
        options = [
            click.Option(
                ["--box-app-config"],
                default=None,
                help="Path to Box app credentials as json file.",
            ),
        ]
        cmd.params.extend(options)


@click.group(name="box", invoke_without_command=True, cls=Group)
@click.pass_context
def box_source(ctx: click.Context, **options):
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
        BoxCliConfig.from_dict(options)
        box_fn(read_config=read_config, partition_config=partition_config, **options)
    except Exception as e:
        logger.error(e, exc_info=True)
        raise click.ClickException(str(e)) from e


@click.command(name="box")
@click.pass_context
def box_dest(ctx: click.Context, **options):
    parent_options: dict = ctx.parent.params if ctx.parent else {}
    # Click sets all multiple fields as tuple, this needs to be updated to list
    for k, v in options.items():
        if isinstance(v, tuple):
            options[k] = list(v)
    for k, v in parent_options.items():
        if isinstance(v, tuple):
            parent_options[k] = list(v)
    verbose = parent_options.get("verbose", False)
    ingest_log_streaming_init(logging.DEBUG if verbose else logging.INFO)
    log_options(parent_options, verbose=verbose)
    log_options(options, verbose=verbose)
    try:
        # run_init_checks(**options)
        read_config = CliReadConfig.from_dict(parent_options)
        partition_config = CliPartitionConfig.from_dict(parent_options)
        # Run for schema validation
        BoxCliConfig.from_dict(options)
        box_fn(
            read_config=read_config,
            partition_config=partition_config,
            writer_type="box",
            writer_kwargs=options,
            **parent_options,
        )
    except Exception as e:
        logger.error(e, exc_info=True)
        raise click.ClickException(str(e)) from e


def get_dest_cmd() -> click.Command:
    cmd = box_dest
    BoxCliConfig.add_cli_options(cmd)
    CliRemoteUrlConfig.add_cli_options(cmd)
    return cmd


def get_source_cmd() -> click.Group:
    cmd = box_source
    BoxCliConfig.add_cli_options(cmd)
    CliRemoteUrlConfig.add_cli_options(cmd)
    CliRecursiveConfig.add_cli_options(cmd)

    # Common CLI configs
    CliReadConfig.add_cli_options(cmd)
    CliPartitionConfig.add_cli_options(cmd)
    cmd.params.append(click.Option(["-v", "--verbose"], is_flag=True, default=False))
    return cmd
