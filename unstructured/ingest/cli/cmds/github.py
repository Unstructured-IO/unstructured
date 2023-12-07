import typing as t
from dataclasses import dataclass

import click

from unstructured.ingest.cli.base.src import BaseSrcCmd
from unstructured.ingest.cli.interfaces import CliConfig, DelimitedString
from unstructured.ingest.connector.github import SimpleGitHubConfig


@dataclass
class GithubCliConfig(SimpleGitHubConfig, CliConfig):
    @staticmethod
    def get_cli_options() -> t.List[click.Option]:
        options = [
            click.Option(
                ["--url"],
                required=True,
                type=str,
                help="URL to GitHub repository, e.g. "
                '"https://github.com/Unstructured-IO/unstructured", or '
                'a repository owner/name pair, e.g. "Unstructured-IO/unstructured"',
            ),
            click.Option(
                ["--git-access-token"],
                default=None,
                help="A GitHub or GitLab access token, "
                "see https://docs.github.com/en/authentication or "
                "https://docs.gitlab.com/ee/api/rest/index.html#personalprojectgroup-access-tokens",
            ),
            click.Option(
                ["--git-branch"],
                default=None,
                type=str,
                help="The branch for which to fetch files from. If not given,"
                " the default repository branch is used.",
            ),
            click.Option(
                ["--git-file-glob"],
                default=None,
                type=DelimitedString(),
                help="A comma-separated list of file globs to limit which "
                "types of files are accepted, e.g. '*.html,*.txt'",
            ),
        ]
        return options


def get_base_src_cmd() -> BaseSrcCmd:
    cmd_cls = BaseSrcCmd(
        cmd_name="github",
        cli_config=GithubCliConfig,
    )
    return cmd_cls
