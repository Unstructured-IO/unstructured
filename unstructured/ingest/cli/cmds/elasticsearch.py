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
from unstructured.ingest.runner import elasticsearch as elasticsearch_fn


@click.command()
@click.option(
    "--index-name",
    required=True,
    help="Name for the Elasticsearch index to pull data from",
)
@click.option(
    "--jq-query",
    default=None,
    help="JQ query to get and concatenate a subset of the fields from a JSON document. "
    "For a group of JSON documents, it assumes that all of the documents have the same schema. "
    "Currently only supported for the Elasticsearch connector. "
    "Example: --jq-query '{meta, body}'",
)
@click.option(
    "--url",
    required=True,
    help='URL to the Elasticsearch cluster, e.g. "http://localhost:9200"',
)
def elasticsearch(**options):
    verbose = options.get("verbose", False)
    ingest_log_streaming_init(logging.DEBUG if verbose else logging.INFO)
    log_options(options)
    try:
        run_init_checks(**options)
        connector_config = map_to_standard_config(options)
        processor_config = map_to_processor_config(options)
        elasticsearch_fn(
            connector_config=connector_config,
            processor_config=processor_config,
            **options,
        )
    except Exception as e:
        logger.error(e, exc_info=True)
        raise click.ClickException(str(e)) from e


def get_cmd() -> click.Command:
    cmd = elasticsearch
    add_shared_options(cmd)
    return cmd
