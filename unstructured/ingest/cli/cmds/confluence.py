import logging
import typing as t
from dataclasses import dataclass

import click

from unstructured.ingest.cli.cmds.utils import (
    DelimitedString,
    Group,
    conform_click_options,
)
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
from unstructured.ingest.runner import confluence as confluence_fn


@dataclass
class ConfluenceCliConfig(BaseConfig, CliMixin):
    api_token: str
    url: str
    user_email: str
    spaces: t.Optional[t.List[str]] = None
    max_num_of_docs_from_each_space: int = 100
    max_num_of_spaces: int = 500

    @staticmethod
    def add_cli_options(cmd: click.Command) -> None:
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
        cmd.params.extend(options)


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
        # run_init_checks(**options)
        read_config = CliReadConfig.from_dict(options)
        partition_config = CliPartitionConfig.from_dict(options)
        # Run for schema validation
        ConfluenceCliConfig.from_dict(options)
        confluence_fn(read_config=read_config, partition_config=partition_config, **options)
    except Exception as e:
        logger.error(e, exc_info=True)
        raise click.ClickException(str(e)) from e


def get_source_cmd() -> click.Group:
    cmd = confluence_source
    ConfluenceCliConfig.add_cli_options(cmd)

    # Common CLI configs
    CliReadConfig.add_cli_options(cmd)
    CliPartitionConfig.add_cli_options(cmd)
    cmd.params.append(click.Option(["-v", "--verbose"], is_flag=True, default=False))
    return cmd
