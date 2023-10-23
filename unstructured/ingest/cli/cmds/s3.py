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
    conform_click_options,
    orchestrate_runner,
)
from unstructured.ingest.interfaces import BaseConfig
from unstructured.ingest.logger import ingest_log_streaming_init, logger


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


def get_base_src_cmd():
    from unstructured.ingest.cli.base.src import BaseSrcCmd

    cmd_cls = BaseSrcCmd(cmd_name="s3", cli_config=S3CliConfig, is_fsspec=True)
    return cmd_cls


def get_base_dest_cmd():
    from unstructured.ingest.cli.base.dest import BaseDestCmd

    cmd_cls = BaseDestCmd(cmd_name="s3", cli_config=S3CliConfig, is_fsspec=True)
    return cmd_cls
