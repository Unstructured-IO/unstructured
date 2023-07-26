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
    help="Comma separated list of Slack channel IDs to pull messages from, "
    "can be a public or private channel",
)
@click.option(
    "--token",
    required=True,
    help="Bot token used to access Slack API, must have channels:history " "scope for the bot user",
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
def slack(
    ctx,
    channels,
    token,
    start_date,
    end_date,
):
    context_dict = ctx.obj
    ingest_log_streaming_init(logging.DEBUG if context_dict["verbose"] else logging.INFO)

    logger.debug(f"parent params: {context_dict}")
    logger.debug(
        "params: {}".format(
            {
                "channels": channels,
                "token": token,
                "start_date": start_date,
                "end_date": end_date,
            },
        ),
    )
    hashed_dir_name = hashlib.sha256(
        channels.encode("utf-8"),
    )
    update_download_dir_hash(ctx_dict=context_dict, hashed_dir_name=hashed_dir_name, logger=logger)

    from unstructured.ingest.connector.slack import (
        SimpleSlackConfig,
        SlackConnector,
    )

    doc_connector = SlackConnector(  # type: ignore
        standard_config=map_to_standard_config(context_dict),
        config=SimpleSlackConfig(
            channels=SimpleSlackConfig.parse_channels(channels),
            token=token,
            oldest=start_date,
            latest=end_date,
            verbose=context_dict["verbose"],
        ),
    )

    process_documents(doc_connector=doc_connector, ctx_dict=context_dict)
