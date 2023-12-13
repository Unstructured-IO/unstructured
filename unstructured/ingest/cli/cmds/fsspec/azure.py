import typing as t
from dataclasses import dataclass

import click

from unstructured.ingest.cli.base.src import BaseSrcCmd
from unstructured.ingest.cli.interfaces import (
    CliConfig,
)
from unstructured.ingest.connector.fsspec.azure import (
    AzureWriteConfig,
    SimpleAzureBlobStorageConfig,
)

CMD_NAME = "azure"


@dataclass
class AzureCliConfig(SimpleAzureBlobStorageConfig, CliConfig):
    @staticmethod
    def get_cli_options() -> t.List[click.Option]:
        options = [
            click.Option(
                ["--account-key"],
                default=None,
                help="The storage account key. This is used for shared key "
                "authentication. If any of account key, sas token or "
                "client_id are not specified, anonymous access will be used.",
            ),
            click.Option(
                ["--account-name"],
                default=None,
                help="The storage account name. This is used to authenticate "
                "requests signed with an account key and to construct "
                "the storage endpoint. It is required unless a connection "
                "string is given, or if a custom domain is used with "
                "anonymous authentication.",
            ),
            click.Option(
                ["--connection-string"],
                default=None,
                help="If specified, this will override all other parameters. See "
                "http://azure.microsoft.com/en-us/documentation/articles/storage-configure-connection-string/ "  # noqa: E501
                "for the connection string format.",
            ),
            click.Option(
                ["--sas_token"],
                default=None,
                help="A shared access signature token to use to authenticate "
                "requests instead of the account key. If account key and "
                "sas token are both specified, account key will be used "
                "to sign. If any of account key, sas token or client_id "
                "are not specified, anonymous access will be used.",
            ),
        ]
        return options


@dataclass
class AzureCliWriteConfig(AzureWriteConfig, CliConfig):
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
    cmd_cls = BaseSrcCmd(
        cmd_name=CMD_NAME,
        cli_config=AzureCliConfig,
        is_fsspec=True,
    )
    return cmd_cls


def get_base_dest_cmd():
    from unstructured.ingest.cli.base.dest import BaseDestCmd

    cmd_cls = BaseDestCmd(
        cmd_name=CMD_NAME,
        cli_config=AzureCliConfig,
        write_config=AzureCliWriteConfig,
        is_fsspec=True,
        additional_cli_options=[AzureCliWriteConfig],
    )
    return cmd_cls
