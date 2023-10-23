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
from unstructured.ingest.runner import JiraRunner


@dataclass
class JiraCliConfig(BaseConfig, CliMixin):
    api_token: str
    url: str
    user_email: str
    projects: t.Optional[t.List[str]] = None
    boards: t.Optional[t.List[str]] = None
    issues: t.Optional[t.List[str]] = None

    @staticmethod
    def get_cli_options() -> t.List[click.Option]:
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
        return options


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
        configs = extract_configs(options, validate=([JiraCliConfig]))
        runner = JiraRunner(
            **configs,  # type: ignore
        )
        runner.run(**options)
    except Exception as e:
        logger.error(e, exc_info=True)
        raise click.ClickException(str(e)) from e


def get_source_cmd() -> click.Group:
    cmd = jira_source
    add_options(cmd, extras=[JiraCliConfig])
    return cmd
