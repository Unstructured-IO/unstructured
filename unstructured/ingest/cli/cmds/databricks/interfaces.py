import typing as t
from dataclasses import dataclass

import click

from unstructured.ingest.cli.interfaces import (
    CliMixin,
)
from unstructured.ingest.interfaces import BaseConfig, WriteConfig


@dataclass
class AuthConfig(BaseConfig, CliMixin):
    pass


@dataclass
class DatabricksVolumesWriteConfig(WriteConfig, CliMixin):
    overwrite: bool = False

    @staticmethod
    def get_cli_options() -> t.List[click.Option]:
        options = [
            click.Option(
                ["--overwrite"],
                is_flag=True,
                default=False,
                help="If true, an existing file will be overwritten.",
            )
        ]
        return options
