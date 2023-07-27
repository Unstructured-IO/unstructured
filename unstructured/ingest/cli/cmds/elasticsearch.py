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
    elasticsearch_fn(**options)


def elasticsearch_fn(**options):
    run_init_checks(options=options)
    ingest_log_streaming_init(logging.DEBUG if options["verbose"] else logging.INFO)
    log_options(options=options)

    hashed_dir_name = hashlib.sha256(
        "{url}_{index_name}".format(url=options["url"], index_name=options["index_name"]).encode(
            "utf-8",
        ),
    )
    update_download_dir_hash(options=options, hashed_dir_name=hashed_dir_name, logger=logger)

    from unstructured.ingest.connector.elasticsearch import (
        ElasticsearchConnector,
        SimpleElasticsearchConfig,
    )

    doc_connector = ElasticsearchConnector(  # type: ignore
        standard_config=map_to_standard_config(options=options),
        config=SimpleElasticsearchConfig(
            url=options["url"],
            index_name=options["index_name"],
            jq_query=options["jq_query"],
        ),
    )

    process_documents(doc_connector=doc_connector, options=options)
