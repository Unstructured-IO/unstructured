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
    "--auto-suggest",
    default=True,
    help="Whether to automatically suggest a page if the exact page was not found."
    " Set to False if the wrong Wikipedia page is fetched.",
)
@click.option(
    "--page-title",
    required=True,
    help='Title of a Wikipedia page, e.g. "Open source software".',
)
def wikipedia(**options):
    wikipedia_fn(**options)


def wikipedia_fn(**options):
    run_init_checks(options=options)
    ingest_log_streaming_init(logging.DEBUG if options["verbose"] else logging.INFO)
    log_options(options=options)

    hashed_dir_name = hashlib.sha256(
        options["page_title"].encode("utf-8"),
    )
    update_download_dir_hash(options=options, hashed_dir_name=hashed_dir_name, logger=logger)

    from unstructured.ingest.connector.wikipedia import (
        SimpleWikipediaConfig,
        WikipediaConnector,
    )

    doc_connector = WikipediaConnector(  # type: ignore
        standard_config=map_to_standard_config(options=options),
        config=SimpleWikipediaConfig(
            title=options["page_title"],
            auto_suggest=options["auto_suggest"],
        ),
    )

    process_documents(doc_connector=doc_connector, options=options)
