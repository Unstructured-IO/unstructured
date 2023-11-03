import typing as t
from dataclasses import dataclass

import click

from unstructured.ingest.cli.base.src import BaseSrcCmd
from unstructured.ingest.cli.interfaces import (
    CliConfig,
    DelimitedString,
)


@dataclass
class JiraCliConfig(CliConfig):
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


def get_base_src_cmd() -> BaseSrcCmd:
    cmd_cls = BaseSrcCmd(cmd_name="jira", cli_config=JiraCliConfig)
    return cmd_cls
