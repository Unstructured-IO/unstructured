import typing as t
from dataclasses import dataclass

import click

from unstructured.ingest.cli.interfaces import (
    CliConfig,
)
from unstructured.ingest.connector.qdrant import QdrantWriteConfig, SimpleQdrantConfig


@dataclass
class QdrantCliConfig(SimpleQdrantConfig, CliConfig):
    @staticmethod
    def get_cli_options() -> t.List[click.Option]:
        options = [
            click.Option(
                ["--collection-name"],
                required=True,
                type=str,
                help="The name of the Qdrant collection to use.",
            ),
            click.Option(
                ["--location"],
                type=str,
                help="The location of the Qdrant cluster.",
            ),
            click.Option(
                ["--url"],
                type=str,
                help="The location of the Qdrant cluster.",
            ),
            click.Option(
                ["--port"],
                type=int,
                default=6333,
                help="Port of the REST API interface. Default: 6333.",
            ),
            click.Option(
                ["--grpc-port"],
                type=int,
                default=6334,
                help="Port of the gRPC interface. Default: 6334.",
            ),
            click.Option(
                ["--prefer-grpc"],
                type=bool,
                is_flag=True,
                help="Whether to use gPRC interface whenever possible in methods. Default: False.",
            ),
            click.Option(
                ["--https"],
                type=bool,
                is_flag=True,
                help="Whether to use HTTPS(SSL) protocol. Default: False.",
            ),
            click.Option(
                ["--prefix"],
                type=str,
                help="Prefix to add the REST API endpoints.",
            ),
            click.Option(
                ["--timeout"],
                type=int,
                help="Timeout for operations. Default: 5.0 seconds for REST, unlimited for gRPC.",
            ),
            click.Option(
                ["--host"],
                type=str,
                help="Host name of the Qdrant service.",
            ),
            click.Option(
                ["--path"],
                type=str,
                help="Persistence path for QdrantLocal.",
            ),
            click.Option(
                ["--force-disable-check-same-thread"],
                type=bool,
                is_flag=True,
                help="Whether to force disable check same thread for QdrantLocal.",
            ),
            click.Option(
                ["--api-key"],
                type=str,
                help="API key for authentication in Qdrant Cloud. Default: None.",
                envvar="QDRANT_API_KEY",
                show_envvar=True,
            ),
        ]
        return options


@dataclass
class QdrantCliWriteConfig(QdrantWriteConfig, CliConfig):
    @staticmethod
    def get_cli_options() -> t.List[click.Option]:
        options = [
            click.Option(
                ["--batch-size"],
                default=50,
                type=int,
                help="Number of points to upload per batch",
            ),
            click.Option(
                ["--num-processes"],
                default=2,
                type=int,
                help="Number of parallel processes with which to upload",
            ),
        ]
        return options


def get_base_dest_cmd():
    from unstructured.ingest.cli.base.dest import BaseDestCmd

    cmd_cls = BaseDestCmd(
        cmd_name="qdrant",
        cli_config=QdrantCliConfig,
        additional_cli_options=[QdrantCliWriteConfig],
        write_config=QdrantWriteConfig,
    )
    return cmd_cls
