from dataclasses import dataclass

import click

from unstructured.ingest.v2.cli.base import DestCmd
from unstructured.ingest.v2.cli.interfaces import CliConfig
from unstructured.ingest.v2.processes.connectors.milvus import CONNECTOR_TYPE


@dataclass
class MilvusCliConnectionConfig(CliConfig):
    @staticmethod
    def get_cli_options() -> list[click.Option]:
        options = [
            click.Option(
                ["--uri"],
                required=False,
                type=str,
                default=None,
                help="Milvus uri, eg 'http://localhost:19530",
            ),
            click.Option(
                ["--user"],
                required=False,
                type=str,
                default=None,
                help="Milvus user",
            ),
            click.Option(
                ["--password"],
                required=False,
                type=str,
                default=None,
                help="Milvus password",
            ),
            click.Option(
                ["--db-name"],
                required=False,
                type=str,
                default=None,
                help="Milvus database name",
            ),
        ]
        return options


@dataclass
class MilvusCliUploaderConfig(CliConfig):
    @staticmethod
    def get_cli_options() -> list[click.Option]:
        options = [
            click.Option(
                ["--collection-name"],
                required=True,
                type=str,
                help="Milvus collections to write to",
            ),
            click.Option(
                ["--num-of-processes"],
                type=click.IntRange(min=1),
                default=4,
                help="number of processes to use when writing to support parallel writes",
            ),
        ]
        return options


milvus_dest_cmd = DestCmd(
    cmd_name=CONNECTOR_TYPE,
    connection_config=MilvusCliConnectionConfig,
    uploader_config=MilvusCliUploaderConfig,
)
