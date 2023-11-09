import typing as t
from dataclasses import dataclass

import click

from unstructured.ingest.cli.base.src import BaseSrcCmd
from unstructured.ingest.cli.interfaces import (
    CliConfig,
)


@dataclass
class RedditCliConfig(CliConfig):
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


def get_base_src_cmd() -> BaseSrcCmd:
    cmd_cls = BaseSrcCmd(cmd_name="reddit", cli_config=RedditCliConfig)
    return cmd_cls
