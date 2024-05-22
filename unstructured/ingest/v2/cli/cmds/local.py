from dataclasses import dataclass

import click

from unstructured.ingest.v2.cli.base import DestCmd, SrcCmd
from unstructured.ingest.v2.cli.interfaces import CliConfig
from unstructured.ingest.v2.cli.utils import DelimitedString
from unstructured.ingest.v2.processes.connectors.local import CONNECTOR_TYPE


@dataclass
class LocalCliIndexerConfig(CliConfig):
    @staticmethod
    def get_cli_options() -> list[click.Option]:
        options = [
            click.Option(
                ["--input-path"],
                required=True,
                type=click.Path(file_okay=True, dir_okay=True, exists=True),
                help="Path to the location in the local file system that will be processed.",
            ),
            click.Option(
                ["--file-glob"],
                default=None,
                type=DelimitedString(),
                help="A comma-separated list of file globs to limit which types of "
                "local files are accepted, e.g. '*.html,*.txt'",
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
class LocalCliUploaderConfig(CliConfig):
    @staticmethod
    def get_cli_options() -> list[click.Option]:
        options = [
            click.Option(
                ["--output-dir"],
                required=True,
                type=str,
                help="Local path to write partitioned output to",
            )
        ]
        return options


local_src_cmd = SrcCmd(
    cmd_name=CONNECTOR_TYPE,
    indexer_config=LocalCliIndexerConfig,
)

local_dest_cmd = DestCmd(cmd_name=CONNECTOR_TYPE, uploader_config=LocalCliUploaderConfig)
