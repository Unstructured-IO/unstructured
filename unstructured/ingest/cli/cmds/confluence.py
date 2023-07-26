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
    help='URL to Confluence Cloud, e.g. "unstructured-ingest-test.atlassian.net"',
)
@click.option(
    "--user-email",
    default=None,
    help="Email to authenticate into Confluence Cloud",
)
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
    "--max-num-of-spaces",
    default=500,
    help="Number of confluence space ids to be fetched. From each fetched space, \
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
def confluence(
    ctx,
    url,
    user_email,
    api_token,
    list_of_spaces,
    max_num_of_spaces,
    max_num_of_docs_from_each_space,
):
    context_dict = ctx.obj
    ingest_log_streaming_init(logging.DEBUG if context_dict["verbose"] else logging.INFO)

    logger.debug(f"parent params: {context_dict}")
    logger.debug(
        "params: {}".format(
            {
                "url": url,
                "user_email": user_email,
                "api_token": api_token,
                "list_of_spaces": list_of_spaces,
                "max_num_of_spaces": max_num_of_spaces,
                "max_num_of_docs_from_each_space": max_num_of_docs_from_each_space,
            },
        ),
    )
    hashed_dir_name = str(
        hashlib.sha256(
            f"{url}".encode("utf-8"),
        ),
    )
    update_download_dir_hash(ctx_dict=context_dict, hashed_dir_name=hashed_dir_name, logger=logger)

    from unstructured.ingest.connector.confluence import (
        ConfluenceConnector,
        SimpleConfluenceConfig,
    )

    doc_connector = ConfluenceConnector(  # type: ignore
        standard_config=map_to_standard_config(context_dict),
        config=SimpleConfluenceConfig(
            url=url,
            user_email=user_email,
            api_token=api_token,
            list_of_spaces=list_of_spaces,
            max_number_of_spaces=max_num_of_spaces,
            max_number_of_docs_from_each_space=max_num_of_docs_from_each_space,
        ),
    )

    process_documents(doc_connector=doc_connector, ctx_dict=context_dict)
