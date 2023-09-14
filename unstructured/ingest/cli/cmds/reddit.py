import logging
import typing as t
from dataclasses import dataclass

import click

from unstructured.ingest.cli.cmds.utils import Group, conform_click_options
from unstructured.ingest.cli.common import (
    log_options,
)
from unstructured.ingest.cli.interfaces import (
    CliMixin,
    CliPartitionConfig,
    CliReadConfig,
)
from unstructured.ingest.interfaces import BaseConfig
from unstructured.ingest.logger import ingest_log_streaming_init, logger
from unstructured.ingest.runner import reddit as reddit_fn


@dataclass
class RedditCliConfig(BaseConfig, CliMixin):
    client_id: str
    client_secret: str
    subreddit_name: str
    user_agent: str
    search_query: t.Optional[str] = None

    @staticmethod
    def add_cli_options(cmd: click.Command) -> None:
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
        ]
        cmd.params.extend(options)


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
        # run_init_checks(**options)
        read_config = CliReadConfig.from_dict(options)
        partition_config = CliPartitionConfig.from_dict(options)
        # Run for schema validation
        RedditCliConfig.from_dict(options)
        reddit_fn(read_config=read_config, partition_config=partition_config, **options)
    except Exception as e:
        logger.error(e, exc_info=True)
        raise click.ClickException(str(e)) from e


def get_source_cmd() -> click.Group:
    cmd = reddit_source
    RedditCliConfig.add_cli_options(cmd)

    # Common CLI configs
    CliReadConfig.add_cli_options(cmd)
    CliPartitionConfig.add_cli_options(cmd)
    cmd.params.append(click.Option(["-v", "--verbose"], is_flag=True, default=False))
    return cmd
