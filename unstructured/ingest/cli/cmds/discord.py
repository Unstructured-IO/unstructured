import hashlib
import logging

import click

from unstructured.ingest.cli.common import (
    map_to_standard_config,
    process_documents,
    update_download_dir_hash,
)
from unstructured.ingest.logger import ingest_log_streaming_init, logger


@click.command()
@click.pass_context
@click.option(
    "--channels",
    required=True,
    help="A comma separated list of discord channel ids to ingest from.",
)
@click.option(
    "--token",
    required=True,
    help="Bot token used to access Discord API, must have "
    "READ_MESSAGE_HISTORY scope for the bot user",
)
@click.option(
    "--period",
    default=None,
    help="Number of days to go back in the history of discord channels, must be a number",
)
def discord(
    ctx,
    channels,
    token,
    period,
):
    context_dict = ctx.obj
    ingest_log_streaming_init(logging.DEBUG if context_dict["verbose"] else logging.INFO)

    logger.debug(f"parent params: {context_dict}")
    logger.debug(
        "params: {}".format(
            {
                "channels": channels,
                "token": token,
                "period": period,
            },
        ),
    )
    hashed_dir_name = hashlib.sha256(
        channels.encode("utf-8"),
    )
    update_download_dir_hash(ctx_dict=context_dict, hashed_dir_name=hashed_dir_name, logger=logger)

    from unstructured.ingest.connector.discord import (
        DiscordConnector,
        SimpleDiscordConfig,
    )

    doc_connector = DiscordConnector(  # type: ignore
        standard_config=map_to_standard_config(context_dict),
        config=SimpleDiscordConfig(
            channels=SimpleDiscordConfig.parse_channels(channels),
            days=period,
            token=token,
            verbose=context_dict["verbose"],
        ),
    )

    process_documents(doc_connector=doc_connector, ctx_dict=context_dict)
