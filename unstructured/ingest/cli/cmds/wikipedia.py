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
    "--wikipedia-page-title",
    required=True,
    help='Title of a Wikipedia page, e.g. "Open source software".',
)
@click.option(
    "--wikipedia-auto-suggest",
    default=True,
    help="Whether to automatically suggest a page if the exact page was not found."
    " Set to False if the wrong Wikipedia page is fetched.",
)
def wikipedia(
    ctx,
    wikipedia_page_title,
    wikipedia_auto_suggest,
):
    context_dict = ctx.obj
    ingest_log_streaming_init(logging.DEBUG if context_dict["verbose"] else logging.INFO)

    logger.debug(f"parent params: {context_dict}")
    logger.debug(
        "params: {}".format(
            {
                "wikipedia_page_title": wikipedia_page_title,
                "wikipedia_auto_suggest": wikipedia_auto_suggest,
            },
        ),
    )
    hashed_dir_name = str(
        hashlib.sha256(
            wikipedia_page_title.encode("utf-8"),
        ),
    )
    update_download_dir_hash(ctx_dict=context_dict, hashed_dir_name=hashed_dir_name, logger=logger)

    from unstructured.ingest.connector.wikipedia import (
        SimpleWikipediaConfig,
        WikipediaConnector,
    )

    doc_connector = WikipediaConnector(  # type: ignore
        standard_config=map_to_standard_config(context_dict),
        config=SimpleWikipediaConfig(
            title=wikipedia_page_title,
            auto_suggest=wikipedia_auto_suggest,
        ),
    )

    process_documents(doc_connector=doc_connector, ctx_dict=context_dict)
