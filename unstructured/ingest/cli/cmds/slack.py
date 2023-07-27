import hashlib
import logging

import click

from unstructured.ingest.cli.common import (
    log_options,
    map_to_standard_config,
    process_documents,
    run_init_checks,
    update_download_dir_hash,
)
from unstructured.ingest.logger import ingest_log_streaming_init, logger


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
    run_init_checks(options=options)
    ingest_log_streaming_init(logging.DEBUG if options["verbose"] else logging.INFO)
    log_options(options=options)

    hashed_dir_name = hashlib.sha256(
        options["channels"].encode("utf-8"),
    )
    update_download_dir_hash(options=options, hashed_dir_name=hashed_dir_name, logger=logger)

    from unstructured.ingest.connector.slack import (
        SimpleSlackConfig,
        SlackConnector,
    )

    doc_connector = SlackConnector(  # type: ignore
        standard_config=map_to_standard_config(options=options),
        config=SimpleSlackConfig(
            channels=SimpleSlackConfig.parse_channels(options["channels"]),
            token=options["token"],
            oldest=options["start_date"],
            latest=options["end_date"],
            verbose=options["verbose"],
        ),
    )

    process_documents(doc_connector=doc_connector, options=options)
