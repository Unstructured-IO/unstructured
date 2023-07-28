import logging

import click

from unstructured.ingest.cli.common import (
    add_shared_options,
    log_options,
    map_to_processor_config,
    map_to_standard_config,
    run_init_checks,
)
from unstructured.ingest.logger import ingest_log_streaming_init, logger
from unstructured.ingest.runner import biomed as biomed_fn


@click.command()
@click.option(
    "--api-id",
    default=None,
    help="ID parameter for OA Web Service API.",
)
@click.option(
    "--api-from",
    default=None,
    help="From parameter for OA Web Service API.",
)
@click.option(
    "--api-until",
    default=None,
    help="Until parameter for OA Web Service API.",
)
@click.option(
    "--decay",
    default=0.3,
    help="(In float) Factor to multiply the delay between retries.",
)
@click.option(
    "--path",
    default=None,
    help="PMC Open Access FTP Directory Path.",
)
@click.option(
    "--max-request-time",
    default=45,
    help="(In seconds) Max request time to OA Web Service API.",
)
@click.option(
    "--max-retries",
    default=1,
    help="Max requests to OA Web Service API.",
)
def biomed(
    **options,
):
    verbose = options.get("verbose", False)
    ingest_log_streaming_init(logging.DEBUG if verbose else logging.INFO)
    log_options(options)
    try:
        run_init_checks(**options)
        connector_config = map_to_standard_config(options)
        processor_config = map_to_processor_config(options)
        biomed_fn(connector_config=connector_config, processor_config=processor_config, **options)
    except Exception as e:
        logger.error(e, exc_info=True)
        raise click.ClickException(str(e)) from e


def get_cmd() -> click.Command:
    cmd = biomed
    add_shared_options(cmd)
    return cmd
