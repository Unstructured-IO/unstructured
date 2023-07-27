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
    "--api-token",
    required=True,
    help="API Token to authenticate into Confluence Cloud. \
        Check https://developer.atlassian.com/cloud/confluence/basic-auth-for-rest-apis/ \
        for more info.",
)
@click.option(
    "--list-of-spaces",
    default=None,
    help="A list of confluence space ids to be fetched. From each fetched space, \
        --confluence-num-of-docs-from-each-space number of docs will be ingested. \
        --confluence-list-of-spaces and --confluence-num-of-spaces cannot be used at the same time",
)
@click.option(
    "--max-num-of-docs-from-each-space",
    default=100,
    help="Number of documents to be aimed to be ingested from each fetched confluence space. \
        If any space has fewer documents, all the documents from that space will be ingested. \
        Documents are not necessarily ingested in order of creation date.",
)
@click.option(
    "--max-num-of-spaces",
    default=500,
    help="Number of confluence space ids to be fetched. From each fetched space, \
        --confluence-num-of-docs-from-each-space number of docs will be ingested. \
        --confluence-list-of-spaces and --confluence-num-of-spaces cannot be used at the same time",
)
@click.option(
    "--url",
    required=True,
    help='URL to Confluence Cloud, e.g. "unstructured-ingest-test.atlassian.net"',
)
@click.option(
    "--user-email",
    default=None,
    help="Email to authenticate into Confluence Cloud",
)
def confluence(
    **options,
):
    run_init_checks(options=options)
    ingest_log_streaming_init(logging.DEBUG if options["verbose"] else logging.INFO)
    log_options(options=options)

    hashed_dir_name = hashlib.sha256(
        options["url"].encode("utf-8"),
    )
    update_download_dir_hash(options=options, hashed_dir_name=hashed_dir_name, logger=logger)

    from unstructured.ingest.connector.confluence import (
        ConfluenceConnector,
        SimpleConfluenceConfig,
    )

    doc_connector = ConfluenceConnector(  # type: ignore
        standard_config=map_to_standard_config(options=options),
        config=SimpleConfluenceConfig(
            url=options["url"],
            user_email=options["user_email"],
            api_token=options["api_token"],
            list_of_spaces=options["list_of_spaces"],
            max_number_of_spaces=options["max_num_of_spaces"],
            max_number_of_docs_from_each_space=options["max_num_of_docs_from_each_space"],
        ),
    )

    process_documents(doc_connector=doc_connector, options=options)
