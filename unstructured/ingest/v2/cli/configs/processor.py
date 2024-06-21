from dataclasses import dataclass

import click

from unstructured.ingest.v2.cli.interfaces import CliConfig
from unstructured.ingest.v2.interfaces.processor import DEFAULT_WORK_DIR


@dataclass
class ProcessorCliConfig(CliConfig):
    @staticmethod
    def get_cli_options() -> list[click.Option]:
        options = [
            click.Option(
                ["--reprocess"],
                is_flag=True,
                default=False,
                help="Reprocess a downloaded file even if the relevant structured "
                "output .json file in output directory already exists.",
            ),
            click.Option(
                ["--work-dir"],
                type=str,
                default=DEFAULT_WORK_DIR,
                show_default=True,
                help="Where to place working files when processing each step",
            ),
            click.Option(
                ["--num-processes"],
                default=2,
                show_default=True,
                type=click.IntRange(min=1),
                help="Number of parallel processes with which to process docs",
            ),
            click.Option(
                ["--max-connections"],
                default=None,
                show_default=True,
                type=click.IntRange(min=1),
                help="Max number of connections allowed when running an async step",
            ),
            click.Option(
                ["--raise-on-error"],
                is_flag=True,
                default=False,
                help="Is set, will raise error if any doc in the pipeline fail. Otherwise will "
                "log error and continue with other docs",
            ),
            click.Option(
                ["--re-download"],
                is_flag=True,
                default=False,
                help="Re-download files even if they are already present in download dir.",
            ),
            click.Option(
                ["--preserve-downloads"],
                is_flag=True,
                default=False,
                help="Preserve downloaded files. Otherwise each file is removed "
                "after being processed successfully.",
            ),
            click.Option(
                ["--download-only"],
                is_flag=True,
                default=False,
                help="Download any files that are not already present in either --download-dir or "
                "the default download ~/.cache/... location in case --download-dir "
                "is not specified and "
                "skip processing them through unstructured.",
            ),
            click.Option(
                ["--max-docs"],
                default=None,
                type=int,
                help="If specified, process at most the specified number of documents.",
            ),
            click.Option(
                ["--uncompress"],
                type=bool,
                default=False,
                is_flag=True,
                help="Uncompress any archived files. Currently supporting zip and tar "
                "files based on file extension.",
            ),
            click.Option(["--verbose"], is_flag=True, default=False),
            click.Option(["--tqdm"], is_flag=True, default=False, help="Show progress bar"),
        ]
        return options
