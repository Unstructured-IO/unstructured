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
    "--subreddit-name",
    required=True,
    help='The name of a subreddit, without the "r\\", e.g. "machinelearning"',
)
@click.option(
    "--client-id",
    required=True,
    help="The client ID, see "
    "https://praw.readthedocs.io/en/stable/getting_started/quick_start.html#prerequisites"
    " for more information.",
)
@click.option(
    "--client-secret",
    required=True,
    help="The client secret, see "
    "https://praw.readthedocs.io/en/stable/getting_started/quick_start.html#prerequisites"
    " for more information.",
)
@click.option(
    "--user-agent",
    default="Unstructured Ingest Subreddit fetcher",
    help="The user agent to use on the Reddit API, see "
    "https://praw.readthedocs.io/en/stable/getting_started/quick_start.html#prerequisites"
    " for more information.",
)
@click.option(
    "--search-query",
    default=None,
    help="If set, return posts using this query. Otherwise, use hot posts.",
)
@click.option("--num-posts", default=10, help="The number of posts to fetch.")
def reddit(
    ctx,
    subreddit_name,
    client_id,
    client_secret,
    user_agent,
    search_query,
    num_posts,
):
    context_dict = ctx.obj
    ingest_log_streaming_init(logging.DEBUG if context_dict["verbose"] else logging.INFO)

    logger.debug(f"parent params: {context_dict}")
    logger.debug(
        "params: {}".format(
            {
                "subreddit_name": subreddit_name,
                "client_id": client_id,
                "client_secret": client_secret,
                "user_agent": user_agent,
                "search_query": search_query,
                "num_posts": num_posts,
            },
        ),
    )
    hashed_dir_name = hashlib.sha256(
        subreddit_name.encode("utf-8"),
    )
    update_download_dir_hash(ctx_dict=context_dict, hashed_dir_name=hashed_dir_name, logger=logger)

    from unstructured.ingest.connector.reddit import (
        RedditConnector,
        SimpleRedditConfig,
    )

    doc_connector = RedditConnector(  # type: ignore
        standard_config=map_to_standard_config(context_dict),
        config=SimpleRedditConfig(
            subreddit_name=subreddit_name,
            client_id=client_id,
            client_secret=client_secret,
            user_agent=user_agent,
            search_query=search_query,
            num_posts=num_posts,
        ),
    )

    process_documents(doc_connector=doc_connector, ctx_dict=context_dict)
