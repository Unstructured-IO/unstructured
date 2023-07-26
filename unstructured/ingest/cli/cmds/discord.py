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
    "--discord-channels",
    default=None,
    help="A comma separated list of discord channel ids to ingest from.",
)
@click.option(
    "--discord-token",
    default=None,
    help="Bot token used to access Discord API, must have "
    "READ_MESSAGE_HISTORY scope for the bot user",
)
@click.option(
    "--discord-period",
    default=None,
    help="Number of days to go back in the history of discord channels, must be an number",
)
def discord(
    ctx,
    discord_channels,
    discord_token,
    discord_period,
):
    context_dict = ctx.obj
    ingest_log_streaming_init(logging.DEBUG if context_dict["verbose"] else logging.INFO)

    logger.debug(f"parent params: {context_dict}")
    logger.debug(
        "params: {}".format(
            {
                "discord_channels": discord_channels,
                "discord_token": discord_token,
                "discord_period": discord_period,
            },
        ),
    )
    hashed_dir_name = str(
        hashlib.sha256(
            discord_channels.encode("utf-8"),
        ),
    )
    update_download_dir_hash(ctx_dict=context_dict, hashed_dir_name=hashed_dir_name, logger=logger)

    from unstructured.ingest.connector.discord import (
        DiscordConnector,
        SimpleDiscordConfig,
    )

    doc_connector = DiscordConnector(  # type: ignore
        standard_config=map_to_standard_config(context_dict),
        config=SimpleDiscordConfig(
            channels=SimpleDiscordConfig.parse_channels(discord_channels),
            days=discord_period,
            token=discord_token,
            verbose=context_dict["verbose"],
        ),
    )

    process_documents(doc_connector=doc_connector, ctx_dict=context_dict)
