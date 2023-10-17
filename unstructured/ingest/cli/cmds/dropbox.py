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
from unstructured.ingest.cli.utils import Group, add_options, conform_click_options, extract_configs
from unstructured.ingest.interfaces import BaseConfig, FsspecConfig
from unstructured.ingest.logger import ingest_log_streaming_init, logger
from unstructured.ingest.runner import DropboxRunner


@dataclass
class DropboxCliConfig(BaseConfig, CliMixin):
    token: str

    @staticmethod
    def get_cli_options() -> t.List[click.Option]:
        options = [
            click.Option(
                ["--token"],
                required=True,
                help="Dropbox access token.",
            ),
        ]
        return options


@click.group(name="dropbox", invoke_without_command=True, cls=Group)
@click.pass_context
def dropbox_source(ctx: click.Context, **options):
    if ctx.invoked_subcommand:
        return

    conform_click_options(options)
    verbose = options.get("verbose", False)
    ingest_log_streaming_init(logging.DEBUG if verbose else logging.INFO)
    log_options(options, verbose=verbose)
    try:
        configs = extract_configs(
            options,
            validate=[DropboxCliConfig],
            extras={"fsspec_config": FsspecConfig},
        )
        runner = DropboxRunner(
            **configs,  # type: ignore
        )
        runner.run(**options)
    except Exception as e:
        logger.error(e, exc_info=True)
        raise click.ClickException(str(e)) from e


def get_source_cmd() -> click.Group:
    cmd = dropbox_source
    add_options(cmd, extras=[DropboxCliConfig, CliFilesStorageConfig])
    return cmd
