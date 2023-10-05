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
from unstructured.ingest.runner import jira as jira_fn


@dataclass
class JiraCliConfig(BaseConfig, CliMixin):
    api_token: str
    url: str
    user_email: str
    projects: t.Optional[t.List[str]] = None
    boards: t.Optional[t.List[str]] = None
    issues: t.Optional[t.List[str]] = None

    @staticmethod
    def add_cli_options(cmd: click.Command) -> None:
        options = [
            click.Option(
                ["--api-token"],
                required=True,
                type=str,
                help="API Token to authenticate into Jira (into Atlassian). \
                    Check \
                    https://developer.atlassian.com/cloud/jira/platform/basic-auth-for-rest-apis/ \
                    for more info.",
            ),
            click.Option(
                ["--url"],
                required=True,
                type=str,
                help="URL to Atlassian (Jira) Cloud, e.g. "
                '"unstructured-jira-connector-test.atlassian.net"',
            ),
            click.Option(
                ["--user-email"],
                required=True,
                type=str,
                help="Email to authenticate into Atlassian (Jira) Cloud.",
            ),
            click.Option(
                ["--projects"],
                default=None,
                type=DelimitedString(),
                help="Comma-delimited Project ids or keys. Use Jira UI or the "
                "API to find or obtain keys. Alternatively, use API to obtain ids.",
            ),
            click.Option(
                ["--boards"],
                default=None,
                type=DelimitedString(),
                help="Comma-delimited Board ids. Check board URL, or use the "
                "API to find the board ids.",
            ),
            click.Option(
                ["--issues"],
                default=None,
                type=DelimitedString(),
                help="Comma-delimited Issue ids or keys. Use Jira UI or the API to "
                "find or obtain keys. Alternatively, use API to obtain ids.",
            ),
        ]
        cmd.params.extend(options)


@click.group(name="jira", invoke_without_command=True, cls=Group)
@click.pass_context
def jira_source(ctx: click.Context, **options):
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
        JiraCliConfig.from_dict(options)
        jira_fn(read_config=read_config, partition_config=partition_config, **options)
    except Exception as e:
        logger.error(e, exc_info=True)
        raise click.ClickException(str(e)) from e


def get_source_cmd() -> click.Group:
    cmd = jira_source
    JiraCliConfig.add_cli_options(cmd)

    # Common CLI configs
    CliReadConfig.add_cli_options(cmd)
    CliPartitionConfig.add_cli_options(cmd)
    cmd.params.append(click.Option(["-v", "--verbose"], is_flag=True, default=False))
    return cmd
