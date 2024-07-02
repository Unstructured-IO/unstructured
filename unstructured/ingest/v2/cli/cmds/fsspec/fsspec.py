from dataclasses import dataclass

import click

from unstructured.ingest.v2.cli.interfaces import CliConfig
from unstructured.ingest.v2.cli.utils import DelimitedString


@dataclass
class FsspecCliDownloadConfig(CliConfig):
    @staticmethod
    def get_cli_options() -> list[click.Option]:
        return [
            click.Option(
                ["--download-dir"],
                help="Where files are downloaded to, defaults to a location at"
                "`$HOME/.cache/unstructured/ingest/<connector name>/<SHA256>`.",
            ),
        ]


@dataclass
class FsspecCliFileConfig(CliConfig):
    @staticmethod
    def get_cli_options() -> list[click.Option]:
        return [
            click.Option(
                ["--remote-url"],
                required=True,
                help="Remote fsspec URL formatted as `protocol://dir/path`",
            )
        ]


@dataclass
class FsspecCliUploaderConfig(FsspecCliFileConfig):
    @staticmethod
    def get_cli_options() -> list[click.Option]:
        options = super(FsspecCliUploaderConfig, FsspecCliUploaderConfig).get_cli_options()
        options.extend(
            [
                click.Option(
                    ["--overwrite"],
                    is_flag=True,
                    default=False,
                    show_default=True,
                    help="If set, will overwrite content if content already exists",
                )
            ]
        )
        return options


@dataclass
class FsspecCliIndexerConfig(FsspecCliFileConfig):
    @staticmethod
    def get_cli_options() -> list[click.Option]:
        options = super(FsspecCliIndexerConfig, FsspecCliIndexerConfig).get_cli_options()
        options.extend(
            [
                click.Option(
                    ["--recursive"],
                    is_flag=True,
                    default=False,
                    help="Recursively download files in their respective folders "
                    "otherwise stop at the files in provided folder level.",
                ),
                click.Option(
                    ["--file-glob"],
                    default=None,
                    type=DelimitedString(),
                    help="A comma-separated list of file globs to limit which types of "
                    "local files are accepted, e.g. '*.html,*.txt'",
                ),
            ]
        )
        return options
