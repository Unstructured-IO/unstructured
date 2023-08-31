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
from unstructured.ingest.runner import salesforce as salesforce_fn


@click.command()
@click.option(
    "--categories",
    default=None,
    required=True,
    help="Comma separated list of Salesforce categories to download. "
    "Currently only Account, Case, Campaign, EmailMessage, Lead.",
)
@click.option(
    "--username",
    required=True,
    help="Salesforce username usually looks like an email.",
)
@click.option(
    "--consumer-key",
    required=True,
    help="For the Salesforce JWT auth. Found in Consumer Details.",
)
@click.option(
    "--private-key-path",
    required=True,
    help="Path to the private key for the Salesforce JWT auth. Usually named server.key.",
)
def salesforce(**options):
    verbose = options.get("verbose", False)
    ingest_log_streaming_init(logging.DEBUG if verbose else logging.INFO)
    log_options(options)
    try:
        run_init_checks(**options)
        connector_config = map_to_standard_config(options)
        processor_config = map_to_processor_config(options)
        salesforce_fn(
            connector_config=connector_config,
            processor_config=processor_config,
            **options,
        )
    except Exception as e:
        logger.error(e, exc_info=True)
        raise click.ClickException(str(e)) from e


def get_cmd() -> click.Command:
    cmd = salesforce
    add_recursive_option(cmd)
    add_shared_options(cmd)
    return cmd
