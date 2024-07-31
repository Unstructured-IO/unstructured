from dataclasses import dataclass

import click

from unstructured.ingest.v2.cli.base import DestCmd
from unstructured.ingest.v2.cli.interfaces import CliConfig
from unstructured.ingest.v2.processes.connectors.singlestore import CONNECTOR_TYPE


@dataclass
class SingleStoreCliConnectionConfig(CliConfig):
    @staticmethod
    def get_cli_options() -> list[click.Option]:
        options = [
            click.Option(
                ["--host"],
                required=False,
                type=str,
                default=None,
                help="SingleStore host",
            ),
            click.Option(
                ["--port"],
                required=False,
                type=int,
                default=None,
                help="SingleStore port",
            ),
            click.Option(
                ["--user"],
                required=False,
                type=str,
                default=None,
                help="SingleStore user",
            ),
            click.Option(
                ["--password"],
                required=False,
                type=str,
                default=None,
                help="SingleStore password",
            ),
            click.Option(
                ["--database"],
                required=False,
                type=str,
                default=None,
                help="SingleStore database",
            ),
        ]
        return options


@dataclass
class SingleStoreCliUploaderConfig(CliConfig):
    @staticmethod
    def get_cli_options() -> list[click.Option]:
        options = [
            click.Option(
                ["--drop-empty-cols"],
                required=False,
                type=bool,
                is_flag=True,
                default=False,
                help="Drop any columns that have no data",
            ),
        ]
        return options


@dataclass
class SingleStoreCliUploadStagerConfig(CliConfig):
    @staticmethod
    def get_cli_options() -> list[click.Option]:
        return [
            click.Option(
                ["--table-name"],
                required=False,
                type=str,
                help="SingleStore table to write contents to",
            ),
            click.Option(
                ["--batch-size"],
                required=False,
                type=click.IntRange(min=1),
                help="Batch size when writing to SingleStore",
            ),
        ]


singlestore_dest_cmd = DestCmd(
    cmd_name=CONNECTOR_TYPE,
    connection_config=SingleStoreCliConnectionConfig,
    uploader_config=SingleStoreCliUploaderConfig,
    upload_stager_config=SingleStoreCliUploadStagerConfig,
)
