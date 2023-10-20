import logging
import typing as t
from dataclasses import dataclass

import click

from unstructured.ingest.cli.common import (
    log_options,
)
from unstructured.ingest.cli.interfaces import (
    CliFilesStorageConfig,
    CliMixin,
)
from unstructured.ingest.cli.utils import (
    Group,
    add_options,
    conform_click_options,
    extract_configs,
    orchestrate_runner,
)
from unstructured.ingest.interfaces import BaseConfig, FsspecConfig
from unstructured.ingest.logger import ingest_log_streaming_init, logger
from unstructured.ingest.runner import S3Runner


@dataclass
class S3CliConfig(BaseConfig, CliMixin):
    anonymous: bool = False
    endpoint_url: t.Optional[str] = None

    @staticmethod
    def get_cli_options() -> t.List[click.Option]:
        options = [
            click.Option(
                ["--anonymous"],
                is_flag=True,
                default=False,
                help="Connect to s3 without local AWS credentials.",
            ),
            click.Option(
                ["--endpoint-url"],
                type=str,
                default=None,
                help="Use this endpoint_url, if specified. Needed for "
                "connecting to non-AWS S3 buckets.",
            ),
        ]
        return options


@click.group(name="s3", invoke_without_command=True, cls=Group)
@click.pass_context
def s3_source(ctx: click.Context, **options):
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
        configs = extract_configs(
            options,
            validate=[S3CliConfig],
            extras={"fsspec_config": FsspecConfig},
        )
        s3_runner = S3Runner(
            **configs,  # type: ignore
        )
        s3_runner.run(**options)
    except Exception as e:
        logger.error(e, exc_info=True)
        raise click.ClickException(str(e)) from e


@click.command(name="s3")
@click.pass_context
def s3_dest(ctx: click.Context, **options):
    if not ctx.parent:
        raise click.ClickException("destination command called without a parent")
    if not ctx.parent.info_name:
        raise click.ClickException("parent command missing info name")
    source_cmd = ctx.parent.info_name.replace("-", "_")
    parent_options: dict = ctx.parent.params if ctx.parent else {}
    conform_click_options(options)
    verbose = parent_options.get("verbose", False)
    ingest_log_streaming_init(logging.DEBUG if verbose else logging.INFO)
    log_options(parent_options, verbose=verbose)
    log_options(options, verbose=verbose)
    try:
        orchestrate_runner(
            source_cmd=source_cmd,
            writer_type="s3",
            parent_options=parent_options,
            options=options,
            validate=[S3CliConfig, CliFilesStorageConfig],
        )
    except Exception as e:
        logger.error(e, exc_info=True)
        raise click.ClickException(str(e)) from e


def get_dest_cmd() -> click.Command:
    cmd = s3_dest
    S3CliConfig.add_cli_options(cmd)
    CliFilesStorageConfig.add_cli_options(cmd)
    return cmd


def get_source_cmd() -> click.Group:
    cmd = s3_source
    add_options(cmd, extras=[S3CliConfig, CliFilesStorageConfig])
    return cmd
