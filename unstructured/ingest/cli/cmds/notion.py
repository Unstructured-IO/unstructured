import typing as t
from dataclasses import dataclass

import click

from unstructured.ingest.cli.base.src import BaseSrcCmd
from unstructured.ingest.cli.interfaces import (
    CliConfig,
    CliRecursiveConfig,
    DelimitedString,
)


@dataclass
class NotionCliConfig(CliConfig):
    notion_api_key: str
    page_ids: t.Optional[t.List[str]]
    database_ids: t.Optional[t.List[str]]
    max_retries: t.Optional[int] = None
    max_time: t.Optional[float] = None

    @staticmethod
    def get_cli_options() -> t.List[click.Option]:
        options = [
            click.Option(
                ["--notion-api-key"],
                required=True,
                type=str,
                help="API key for Notion api",
            ),
            click.Option(
                ["--page-ids"],
                default=None,
                type=DelimitedString(),
                help="Notion page IDs to pull text from",
            ),
            click.Option(
                ["--database-ids"],
                default=None,
                type=DelimitedString(),
                help="Notion database IDs to pull text from",
            ),
        ]
        return options


def get_base_src_cmd() -> BaseSrcCmd:
    cmd_cls = BaseSrcCmd(
        cmd_name="notion",
        cli_config=NotionCliConfig,
        additional_cli_options=[CliRecursiveConfig],
    )
    return cmd_cls
