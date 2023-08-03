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
from unstructured.ingest.runner import notion as notion_fn


@click.command()
@click.option(
    "--page-ids",
    default=None,
    help="Comma separated list of Notion page IDs to pull text from",
)
@click.option(
    "--database-ids",
    default=None,
    help="Comma separated list of Notion database IDs to pull text from",
)
@click.option(
    "--api-key",
    required=True,
    help="API key for Notion api",
)
def notion(**options):
    verbose = options.get("verbose", False)
    ingest_log_streaming_init(logging.DEBUG if verbose else logging.INFO)
    log_options(options)
    try:
        run_init_checks(**options)
        connector_config = map_to_standard_config(options)
        processor_config = map_to_processor_config(options)
        notion_fn(connector_config=connector_config, processor_config=processor_config, **options)
    except Exception as e:
        logger.error(e, exc_info=True)
        raise click.ClickException(str(e)) from e


def get_cmd() -> click.Command:
    cmd = notion
    add_shared_options(cmd)
    add_recursive_option(cmd)
    return cmd
