import typing as t
from dataclasses import dataclass

import click

from unstructured.ingest.cli.base.src import BaseSrcCmd
from unstructured.ingest.cli.interfaces import (
    CliConfig,
)

CMD_NAME = "azure"


@dataclass
class AzureCliConfig(CliConfig):
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


@dataclass
class AzureCliWriteConfig(CliConfig):
    overwrite: bool = False

    @staticmethod
    def get_cli_options() -> t.List[click.Option]:
        options = [
            click.Option(
                ["--overwrite"],
                is_flag=True,
                default=False,
                show_default=True,
                help="If set, will overwrite content if content already exists",
            )
        ]
        return options


def get_base_src_cmd() -> BaseSrcCmd:
    cmd_cls = BaseSrcCmd(cmd_name=CMD_NAME, cli_config=AzureCliConfig, is_fsspec=True)
    return cmd_cls


def get_base_dest_cmd():
    from unstructured.ingest.cli.base.dest import BaseDestCmd

    cmd_cls = BaseDestCmd(
        cmd_name=CMD_NAME,
        cli_config=AzureCliConfig,
        is_fsspec=True,
        additional_cli_options=[AzureCliWriteConfig],
    )
    return cmd_cls
