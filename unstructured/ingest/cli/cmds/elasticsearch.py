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
    "--url",
    required=True,
    help='URL to the Elasticsearch cluster, e.g. "http://localhost:9200"',
)
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
def elasticsearch(
    ctx,
    url,
    index_name,
    jq_query,
):
    context_dict = ctx.obj
    ingest_log_streaming_init(logging.DEBUG if context_dict["verbose"] else logging.INFO)

    logger.debug(f"parent params: {context_dict}")
    logger.debug(
        "params: {}".format(
            {
                "url": url,
                "index_name": index_name,
                "jq_query": jq_query,
            },
        ),
    )
    hashed_dir_name = hashlib.sha256(
        f"{url}_{index_name}".encode("utf-8"),
    )
    update_download_dir_hash(ctx_dict=context_dict, hashed_dir_name=hashed_dir_name, logger=logger)

    from unstructured.ingest.connector.elasticsearch import (
        ElasticsearchConnector,
        SimpleElasticsearchConfig,
    )

    doc_connector = ElasticsearchConnector(  # type: ignore
        standard_config=map_to_standard_config(context_dict),
        config=SimpleElasticsearchConfig(
            url=url,
            index_name=index_name,
            jq_query=jq_query,
        ),
    )

    process_documents(doc_connector=doc_connector, ctx_dict=context_dict)
