import typing as t
from dataclasses import dataclass

import click

from unstructured.ingest.cli.interfaces import CliConfig, Dict

CMD_NAME = "weaviate"


@dataclass
class WeaviateCliConfig(CliConfig):
    host_url: str
    class_name: str
    auth_keys: t.Optional[t.Dict[str, str]] = None

    @staticmethod
    def get_cli_options() -> t.List[click.Option]:
        options = [
            click.Option(
                ["--host-url"],
                required=True,
                help="Weaviate instance url",
            ),
            click.Option(
                ["--class-name"],
                default=None,
                type=str,
                help="Target class collection name",
            ),
            click.Option(
                ["--auth-keys"], required=False, type=Dict(), help="Key,value pairs representing"
            ),
        ]
        return options


@dataclass
class WeaviateCliWriteConfig(CliConfig):
    batch_size: int

    @staticmethod
    def get_cli_options() -> t.List[click.Option]:
        options = [
            click.Option(
                ["--batch-size"],
                default=100,
                type=int,
                help="Batch insert size",
            )
        ]
        return options


def get_base_dest_cmd():
    from unstructured.ingest.cli.base.dest import BaseDestCmd

    cmd_cls = BaseDestCmd(
        cmd_name=CMD_NAME,
        cli_config=WeaviateCliConfig,
        additional_cli_options=[WeaviateCliWriteConfig],
    )
    return cmd_cls
