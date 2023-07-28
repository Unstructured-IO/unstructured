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
from unstructured.ingest.runner import discord as discord_fn


@click.command()
@click.option(
    "--channels",
    required=True,
    help="A comma separated list of discord channel ids to ingest from.",
)
@click.option(
    "--period",
    default=None,
    help="Number of days to go back in the history of discord channels, must be a number",
)
@click.option(
    "--token",
    required=True,
    help="Bot token used to access Discord API, must have "
    "READ_MESSAGE_HISTORY scope for the bot user",
)
def discord(**options):
    verbose = options.get("verbose", False)
    ingest_log_streaming_init(logging.DEBUG if verbose else logging.INFO)
    log_options(options)
    try:
        run_init_checks(**options)
        connector_config = map_to_standard_config(options)
        processor_config = map_to_processor_config(options)
        discord_fn(connector_config=connector_config, processor_config=processor_config, **options)
    except Exception as e:
        logger.error(e, exc_info=True)
        raise click.ClickException(str(e)) from e


def get_cmd() -> click.Command:
    cmd = discord
    add_shared_options(cmd)
    return cmd
