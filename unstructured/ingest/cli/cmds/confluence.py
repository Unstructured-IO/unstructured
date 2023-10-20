import logging
import typing as t
from dataclasses import dataclass

import click

from unstructured.ingest.cli.common import (
    log_options,
)
from unstructured.ingest.cli.interfaces import (
    CliMixin,
    DelimitedString,
)
from unstructured.ingest.cli.utils import Group, add_options, conform_click_options, extract_configs
from unstructured.ingest.interfaces import BaseConfig
from unstructured.ingest.logger import ingest_log_streaming_init, logger
from unstructured.ingest.runner import ConfluenceRunner


@dataclass
class ConfluenceCliConfig(BaseConfig, CliMixin):
    api_token: str
    url: str
    user_email: str
    spaces: t.Optional[t.List[str]] = None
    max_num_of_docs_from_each_space: int = 100
    max_num_of_spaces: int = 500

    @staticmethod
    def get_cli_options() -> t.List[click.Option]:
        options = [
            click.Option(
                ["--api-token"],
                required=True,
                help="API Token to authenticate into Confluence Cloud. "
                "Check "
                "https://developer.atlassian.com/cloud/confluence/basic-auth-for-rest-apis/ "
                "for more info.",
            ),
            click.Option(
                ["--url"],
                required=True,
                help='URL to Confluence Cloud, e.g. "unstructured-ingest-test.atlassian.net"',
            ),
            click.Option(
                ["--user-email"],
                required=True,
                help="Email to authenticate into Confluence Cloud",
            ),
            click.Option(
                ["--spaces"],
                default=None,
                type=DelimitedString(),
                help="A list of confluence space ids to be fetched. From each fetched space, "
                "--num-of-docs-from-each-space number of docs will be ingested. "
                "--spaces and --num-of-spaces cannot be used at the same time",
            ),
            click.Option(
                ["--max-num-of-docs-from-each-space"],
                default=100,
                help="Number of documents to be aimed to be ingested from each fetched "
                "confluence space. If any space has fewer documents, all the documents from "
                "that space will be ingested. Documents are not necessarily "
                "ingested in order of creation date.",
            ),
            click.Option(
                ["--max-num-of-spaces"],
                default=500,
                help="Number of confluence space ids to be fetched. From each fetched space, "
                "--num-of-docs-from-each-space number of docs will be ingested. "
                "--spaces and --num-of-spaces cannot be used at the same time",
            ),
        ]
        return options


@click.group(name="confluence", invoke_without_command=True, cls=Group)
@click.pass_context
def confluence_source(ctx: click.Context, **options):
    if ctx.invoked_subcommand:
        return

    conform_click_options(options)
    verbose = options.get("verbose", False)
    ingest_log_streaming_init(logging.DEBUG if verbose else logging.INFO)
    log_options(options, verbose=verbose)
    try:
        configs = extract_configs(options, validate=[ConfluenceCliConfig])
        runner = ConfluenceRunner(
            **configs,  # type: ignore
        )
        runner.run(**options)
    except Exception as e:
        logger.error(e, exc_info=True)
        raise click.ClickException(str(e)) from e


def get_source_cmd() -> click.Group:
    cmd = confluence_source
    add_options(cmd, extras=[ConfluenceCliConfig])
    return cmd
