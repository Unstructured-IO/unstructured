import logging

import click

from unstructured.ingest.cli.common import (
    log_options,
)
from unstructured.ingest.cli.interfaces import (
    CliFilesStorageConfig,
)
from unstructured.ingest.cli.utils import Group, add_options, conform_click_options, extract_configs
from unstructured.ingest.interfaces import (
    FsspecConfig,
)
from unstructured.ingest.logger import ingest_log_streaming_init, logger
from unstructured.ingest.runner import FsspecRunner


@click.group(name="fsspec", invoke_without_command=True, cls=Group)
@click.pass_context
def fsspec_source(ctx: click.Context, **options):
    if ctx.invoked_subcommand:
        return

    conform_click_options(options)
    verbose = options.get("verbose", False)
    ingest_log_streaming_init(logging.DEBUG if verbose else logging.INFO)
    log_options(options, verbose=verbose)
    try:
        configs = extract_configs(options, extras={"fsspec_config": FsspecConfig})
        runner = FsspecRunner(
            **configs,  # type: ignore
        )
        runner.run(**options)
    except Exception as e:
        logger.error(e, exc_info=True)
        raise click.ClickException(str(e)) from e


def get_source_cmd() -> click.Group:
    cmd = fsspec_source
    add_options(cmd, extras=[CliFilesStorageConfig])
    return cmd
