import typing as t
from dataclasses import dataclass

import click

from unstructured.ingest.cli.base.src import BaseSrcCmd
from unstructured.ingest.cli.interfaces import (
    CliConfig,
    DelimitedString,
)
from unstructured.ingest.connector.confluence import SimpleConfluenceConfig


@dataclass
class ConfluenceCliConfig(SimpleConfluenceConfig, CliConfig):
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


def get_base_src_cmd() -> BaseSrcCmd:
    cmd_cls = BaseSrcCmd(
        cmd_name="confluence",
        cli_config=ConfluenceCliConfig,
    )
    return cmd_cls
