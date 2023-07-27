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
@click.option("--num-posts", default=10, help="The number of posts to fetch.")
@click.option(
    "--search-query",
    default=None,
    help="If set, return posts using this query. Otherwise, use hot posts.",
)
@click.option(
    "--subreddit-name",
    required=True,
    help='The name of a subreddit, without the "r\\", e.g. "machinelearning"',
)
@click.option(
    "--user-agent",
    default="Unstructured Ingest Subreddit fetcher",
    help="The user agent to use on the Reddit API, see "
    "https://praw.readthedocs.io/en/stable/getting_started/quick_start.html#prerequisites"
    " for more information.",
)
def reddit(**options):
    reddit_fn(**options)


def reddit_fn(**options):
    run_init_checks(options=options)
    ingest_log_streaming_init(logging.DEBUG if options["verbose"] else logging.INFO)
    log_options(options=options)

    hashed_dir_name = hashlib.sha256(
        options["subreddit_name"].encode("utf-8"),
    )
    update_download_dir_hash(options=options, hashed_dir_name=hashed_dir_name, logger=logger)

    from unstructured.ingest.connector.reddit import (
        RedditConnector,
        SimpleRedditConfig,
    )

    doc_connector = RedditConnector(  # type: ignore
        standard_config=map_to_standard_config(options=options),
        config=SimpleRedditConfig(
            subreddit_name=options["subreddit_name"],
            client_id=options["client_id"],
            client_secret=options["client_secret"],
            user_agent=options["user_agent"],
            search_query=options["user_agent"],
            num_posts=options["num_posts"],
        ),
    )

    process_documents(doc_connector=doc_connector, options=options)
