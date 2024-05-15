import typing as t
from dataclasses import dataclass

import click

from unstructured.ingest.cli.interfaces import CliConfig, Dict
from unstructured.ingest.connector.kdbai import KDBAIWriteConfig, SimpleKDBAIConfig


@dataclass
class KDBAICliConfig(SimpleKDBAIConfig, CliConfig):
    @staticmethod
    def get_cli_options() -> t.List[click.Option]:
        options = [
            click.Option(
                ["--endpoint"],
                required=False,
                default="http://localhost:8082",
                help="Endpoint url where KDBAI is hosted.",
            ),
            click.Option(
                ["--api-key"],
                required=False,
                type=str,
                default=None,
                help="A string for the api-key, can be left empty when connecting to local KDBAI instance.",
            ),
            click.Option(
                ["--table-name"],
                required=True,
                type=str,
                help="The name of the KDBAI table to write into.",
            ),
        ]
        return options


@dataclass
class KDBAICliWriteConfig(KDBAIWriteConfig, CliConfig):
    @staticmethod
    def get_cli_options() -> t.List[click.Option]:
        options = [
            click.Option(
                ["--batch-size"],
                default=100,
                type=int,
                help="Number of records per batch",
            ),
        ]
        return options


def get_base_dest_cmd():
    from unstructured.ingest.cli.base.dest import BaseDestCmd

    cmd_cls = BaseDestCmd(
        cmd_name="kdbai",
        cli_config=KDBAICliConfig,
        additional_cli_options=[KDBAICliWriteConfig],
        write_config=KDBAIWriteConfig,
    )
    return cmd_cls
