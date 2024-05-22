from dataclasses import dataclass

import click

from unstructured.ingest.v2.cli.base import DestCmd, SrcCmd
from unstructured.ingest.v2.cli.cmds.fsspec.fsspec import (
    FsspecCliDownloadConfig,
    FsspecCliIndexerConfig,
    FsspecCliUploaderConfig,
)
from unstructured.ingest.v2.cli.interfaces import CliConfig
from unstructured.ingest.v2.processes.connectors.fsspec.sftp import (
    CONNECTOR_TYPE,
)


@dataclass
class SftpCliDownloadConfig(FsspecCliDownloadConfig):
    pass


@dataclass
class SftpCliIndexerConfig(FsspecCliIndexerConfig):
    pass


@dataclass
class SftpCliConnectionConfig(CliConfig):
    @staticmethod
    def get_cli_options() -> list[click.Option]:
        options = [
            click.Option(
                ["--username"],
                required=True,
                type=str,
                help="Username for sftp connection",
            ),
            click.Option(
                ["--password"],
                required=True,
                type=str,
                help="Password for sftp connection",
            ),
            click.Option(
                ["--look-for-keys"],
                required=False,
                default=False,
                is_flag=True,
                type=bool,
                help="Whether to search for private key files in ~/.ssh/",
            ),
            click.Option(
                ["--allow-agent"],
                required=False,
                default=False,
                is_flag=True,
                type=bool,
                help="Whether to connect to the SSH agent.",
            ),
        ]
        return options


@dataclass
class SftpUploaderConfig(FsspecCliUploaderConfig):
    pass


sftp_src_cmd = SrcCmd(
    cmd_name=CONNECTOR_TYPE,
    indexer_config=SftpCliIndexerConfig,
    connection_config=SftpCliConnectionConfig,
    downloader_config=SftpCliDownloadConfig,
)

sftp_dest_cmd = DestCmd(
    cmd_name=CONNECTOR_TYPE,
    connection_config=SftpCliConnectionConfig,
    uploader_config=SftpUploaderConfig,
)
