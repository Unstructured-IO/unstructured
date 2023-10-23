import typing as t
from dataclasses import dataclass

import click

from unstructured.ingest.cli.base.src import BaseSrcCmd
from unstructured.ingest.cli.interfaces import (
    CliMixin,
)
from unstructured.ingest.interfaces import BaseConfig


@dataclass
class AzureCliConfig(BaseConfig, CliMixin):
    account_id: t.Optional[str] = None
    account_name: t.Optional[str] = None
    connection_string: t.Optional[str] = None

    @staticmethod
    def get_cli_options() -> t.List[click.Option]:
        options = [
            click.Option(
                ["--account-key"],
                default=None,
                help="Azure Blob Storage or DataLake account key (not required if "
                "`azure_account_name` is public).",
            ),
            click.Option(
                ["--account-name"],
                default=None,
                help="Azure Blob Storage or DataLake account name.",
            ),
            click.Option(
                ["--connection-string"],
                default=None,
                help="Azure Blob Storage or DataLake connection string.",
            ),
        ]
        return options


def get_base_src_cmd() -> BaseSrcCmd:
    cmd_cls = BaseSrcCmd(cmd_name="azure", cli_config=AzureCliConfig, is_fsspec=True)
    return cmd_cls
