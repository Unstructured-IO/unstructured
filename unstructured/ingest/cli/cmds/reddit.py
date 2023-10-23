import logging
import typing as t
from dataclasses import dataclass

import click

from unstructured.ingest.cli.common import (
    log_options,
)
from unstructured.ingest.cli.interfaces import (
    CliMixin,
)
from unstructured.ingest.cli.utils import Group, add_options, conform_click_options, extract_configs
from unstructured.ingest.interfaces import BaseConfig
from unstructured.ingest.logger import ingest_log_streaming_init, logger
from unstructured.ingest.runner import RedditRunner


@dataclass
class RedditCliConfig(BaseConfig, CliMixin):
    client_id: str
    client_secret: str
    subreddit_name: str
    user_agent: str
    num_posts: int
    search_query: t.Optional[str] = None

    @staticmethod
    def get_cli_options() -> t.List[click.Option]:
        options = [
            click.Option(
                ["--client-id"],
                required=True,
                type=str,
                help="The client ID, see "
                "https://praw.readthedocs.io/en/stable/getting_started/quick_start.html#prerequisites"  # noqa: E501
                " for more information.",
            ),
            click.Option(
                ["--client-secret"],
                required=True,
                type=str,
                help="The client secret, see "
                "https://praw.readthedocs.io/en/stable/getting_started/quick_start.html#prerequisites"  # noqa: E501
                " for more information.",
            ),
            click.Option(
                ["--subreddit-name"],
                required=True,
                type=str,
                help='The name of a subreddit, without the "r\\", e.g. "machinelearning"',
            ),
            click.Option(
                ["--search-query"],
                default=None,
                type=str,
                help="If set, return posts using this query. Otherwise, use hot posts.",
            ),
            click.Option(
                ["--num-posts"],
                required=True,
                type=click.IntRange(0),
                help="If set, limits the number of posts to pull in.",
            ),
            click.Option(
                ["--user-agent"],
                required=True,
                type=str,
                help="user agent request header to use when calling Reddit API",
            ),
        ]
        return options


@click.group(name="reddit", invoke_without_command=True, cls=Group)
@click.pass_context
def reddit_source(ctx: click.Context, **options):
    if ctx.invoked_subcommand:
        return

    conform_click_options(options)
    verbose = options.get("verbose", False)
    ingest_log_streaming_init(logging.DEBUG if verbose else logging.INFO)
    log_options(options, verbose=verbose)
    try:
        configs = extract_configs(options, validate=([RedditCliConfig]))
        runner = RedditRunner(
            **configs,  # type: ignore
        )
        runner.run(**options)
    except Exception as e:
        logger.error(e, exc_info=True)
        raise click.ClickException(str(e)) from e


def get_source_cmd() -> click.Group:
    cmd = reddit_source
    add_options(cmd, extras=[RedditCliConfig])
    return cmd
