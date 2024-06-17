from dataclasses import dataclass

import click

from unstructured.ingest.v2.cli.base import DestCmd, SrcCmd
from unstructured.ingest.v2.cli.cmds.fsspec.fsspec import (
    FsspecCliDownloadConfig,
    FsspecCliIndexerConfig,
    FsspecCliUploaderConfig,
)
from unstructured.ingest.v2.cli.interfaces import CliConfig
from unstructured.ingest.v2.processes.connectors.fsspec.azure import (
    CONNECTOR_TYPE,
)


@dataclass
class AzureCliDownloadConfig(FsspecCliDownloadConfig):
    pass


@dataclass
class AzureCliIndexerConfig(FsspecCliIndexerConfig):
    pass


@dataclass
class AzureCliConnectionConfig(CliConfig):
    @staticmethod
    def get_cli_options() -> list[click.Option]:
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
class AzureUploaderConfig(FsspecCliUploaderConfig):
    pass


azure_src_cmd = SrcCmd(
    cmd_name=CONNECTOR_TYPE,
    indexer_config=AzureCliIndexerConfig,
    connection_config=AzureCliConnectionConfig,
    downloader_config=AzureCliDownloadConfig,
)

azure_dest_cmd = DestCmd(
    cmd_name=CONNECTOR_TYPE,
    connection_config=AzureCliConnectionConfig,
    uploader_config=AzureUploaderConfig,
)
