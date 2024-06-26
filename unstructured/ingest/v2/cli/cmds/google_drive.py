from dataclasses import dataclass

import click

from unstructured.ingest.v2.cli.base import SrcCmd
from unstructured.ingest.v2.cli.interfaces import CliConfig
from unstructured.ingest.v2.cli.utils import DelimitedString, FileOrJson
from unstructured.ingest.v2.processes.connectors.google_drive import CONNECTOR_TYPE


@dataclass
class GoogleDriveCliConnectionConfig(CliConfig):
    @staticmethod
    def get_cli_options() -> list[click.Option]:
        options = [
            click.Option(
                ["--drive-id"],
                required=True,
                type=str,
                help="Google Drive File or Folder ID.",
            ),
            click.Option(
                ["--service-account-key"],
                required=True,
                type=FileOrJson(),
                help="Either the file path of the credentials file to use or a json string of "
                "those values to use for authentication",
            ),
        ]
        return options


@dataclass
class GoogleDriveCliIndexerConfig(CliConfig):
    @staticmethod
    def get_cli_options() -> list[click.Option]:
        options = [
            click.Option(
                ["--extensions"],
                default=None,
                type=DelimitedString(),
                help="Filters the files to be processed based on extension e.g. jpg, docx, etc.",
            ),
            click.Option(
                ["--recursive"],
                is_flag=True,
                default=False,
                help="Recursively download files in their respective folders "
                "otherwise stop at the files in provided folder level.",
            ),
        ]
        return options


@dataclass
class GoogleDriveCliDownloadConfig(CliConfig):
    @staticmethod
    def get_cli_options() -> list[click.Option]:
        options = [
            click.Option(
                ["--download-dir"],
                help="Where files are downloaded to, defaults to a location at"
                "`$HOME/.cache/unstructured/ingest/<connector name>/<SHA256>`.",
            ),
        ]
        return options


google_drive_src_cmd = SrcCmd(
    cmd_name=CONNECTOR_TYPE,
    connection_config=GoogleDriveCliConnectionConfig,
    indexer_config=GoogleDriveCliIndexerConfig,
    downloader_config=GoogleDriveCliDownloadConfig,
)
