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
from unstructured.ingest.runner import slack as slack_fn


@click.command()
@click.option(
    "--channels",
    required=True,
    help="Comma separated list of Slack channel IDs to pull messages from, "
    "can be a public or private channel",
)
@click.option(
    "--start-date",
    default=None,
    help="Start date/time in formats YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS or "
    "YYYY-MM-DD+HH:MM:SS or YYYY-MM-DDTHH:MM:SStz",
)
@click.option(
    "--end-date",
    default=None,
    help="End date/time in formats YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS or "
    "YYYY-MM-DD+HH:MM:SS or YYYY-MM-DDTHH:MM:SStz",
)
@click.option(
    "--token",
    required=True,
    help="Bot token used to access Slack API, must have channels:history " "scope for the bot user",
)
def slack(**options):
    verbose = options.get("verbose", False)
    ingest_log_streaming_init(logging.DEBUG if verbose else logging.INFO)
    log_options(options)
    try:
        run_init_checks(**options)
        connector_config = map_to_standard_config(options)
        processor_config = map_to_processor_config(options)
        slack_fn(connector_config=connector_config, processor_config=processor_config, **options)
    except Exception as e:
        logger.error(e, exc_info=True)
        raise click.ClickException(str(e)) from e


def get_cmd() -> click.Command:
    cmd = slack
    add_shared_options(cmd)
    return cmd
