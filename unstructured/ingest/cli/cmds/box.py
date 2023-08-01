import logging

import click

from unstructured.ingest.cli.common import (
    add_recursive_option,
    add_remote_url_option,
    add_shared_options,
    log_options,
    map_to_processor_config,
    map_to_standard_config,
    run_init_checks,
)
from unstructured.ingest.logger import ingest_log_streaming_init, logger
from unstructured.ingest.runner import box as box_fn


@click.command()
@click.option(
    "--box-app-config",
    default=None,
    help="Path to Box app credentials as json file.",
)
def box(**options):
    verbose = options.get("verbose", False)
    ingest_log_streaming_init(logging.DEBUG if verbose else logging.INFO)
    log_options(options)
    try:
        run_init_checks(**options)
        connector_config = map_to_standard_config(options)
        processor_config = map_to_processor_config(options)
        box_fn(connector_config=connector_config, processor_config=processor_config, **options)
    except Exception as e:
        logger.error(e, exc_info=True)
        raise click.ClickException(str(e)) from e


def get_cmd() -> click.Command:
    cmd = box
    add_recursive_option(cmd)
    add_shared_options(cmd)
    add_remote_url_option(cmd)
    return cmd
