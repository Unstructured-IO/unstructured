import logging

import click

from unstructured.ingest.cli.common import (
    add_recursive_option,
    add_shared_options,
    log_options,
    map_to_processor_config,
    map_to_standard_config,
    run_init_checks,
)
from unstructured.ingest.logger import ingest_log_streaming_init, logger
from unstructured.ingest.runner import local as local_fn


@click.command()
@click.option(
    "--file-glob",
    default=None,
    help="A comma-separated list of file globs to limit which types of local files are accepted,"
    " e.g. '*.html,*.txt'",
)
@click.option(
    "--input-path",
    required=True,
    help="Path to the location in the local file system that will be processed.",
)
def local(**options):
    verbose = options.get("verbose", False)
    ingest_log_streaming_init(logging.DEBUG if verbose else logging.INFO)
    log_options(options)
    try:
        run_init_checks(**options)
        connector_config = map_to_standard_config(options)
        processor_config = map_to_processor_config(options)
        local_fn(connector_config=connector_config, processor_config=processor_config, **options)
    except Exception as e:
        logger.error(e, exc_info=True)
        raise click.ClickException(str(e)) from e


def get_cmd() -> click.Command:
    cmd = local
    add_shared_options(cmd)
    add_recursive_option(cmd)
    return cmd
