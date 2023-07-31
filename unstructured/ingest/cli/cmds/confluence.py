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
from unstructured.ingest.runner import confluence as confluence_fn


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
    required=True,
    help="Email to authenticate into Confluence Cloud",
)
def confluence(
    **options,
):
    verbose = options.get("verbose", False)
    ingest_log_streaming_init(logging.DEBUG if verbose else logging.INFO)
    log_options(options)
    try:
        run_init_checks(**options)
        connector_config = map_to_standard_config(options)
        processor_config = map_to_processor_config(options)
        confluence_fn(
            connector_config=connector_config,
            processor_config=processor_config,
            **options,
        )
    except Exception as e:
        logger.error(e, exc_info=True)
        raise click.ClickException(str(e)) from e


def get_cmd() -> click.Command:
    cmd = confluence
    add_shared_options(cmd)
    return cmd
