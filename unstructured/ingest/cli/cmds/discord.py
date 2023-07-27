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
    discord_fn(**options)


def discord_fn(**options):
    run_init_checks(options=options)
    ingest_log_streaming_init(logging.DEBUG if options["verbose"] else logging.INFO)
    log_options(options=options)

    hashed_dir_name = hashlib.sha256(
        options["channels"].encode("utf-8"),
    )
    update_download_dir_hash(options=options, hashed_dir_name=hashed_dir_name, logger=logger)

    from unstructured.ingest.connector.discord import (
        DiscordConnector,
        SimpleDiscordConfig,
    )

    doc_connector = DiscordConnector(  # type: ignore
        standard_config=map_to_standard_config(options=options),
        config=SimpleDiscordConfig(
            channels=SimpleDiscordConfig.parse_channels(options["channels"]),
            days=options["period"],
            token=options["token"],
            verbose=options["verbose"],
        ),
    )

    process_documents(doc_connector=doc_connector, options=options)
