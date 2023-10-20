import logging
import typing as t
from dataclasses import dataclass

import click

from unstructured.ingest.cli.common import (
    log_options,
)
from unstructured.ingest.cli.interfaces import (
    CliMixin,
    CliRecursiveConfig,
)
from unstructured.ingest.cli.utils import Group, add_options, conform_click_options, extract_configs
from unstructured.ingest.interfaces import BaseConfig
from unstructured.ingest.logger import ingest_log_streaming_init, logger
from unstructured.ingest.runner import LocalRunner


@dataclass
class LocalCliConfig(BaseConfig, CliMixin):
    input_path: str
    file_glob: t.Optional[str] = None

    @staticmethod
    def get_cli_options() -> t.List[click.Option]:
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
                type=str,
                help="A comma-separated list of file globs to limit which types of "
                "local files are accepted, e.g. '*.html,*.txt'",
            ),
        ]
        return options


@click.group(name="local", invoke_without_command=True, cls=Group)
@click.pass_context
def local_source(ctx: click.Context, **options):
    if ctx.invoked_subcommand:
        return

    conform_click_options(options)
    verbose = options.get("verbose", False)
    ingest_log_streaming_init(logging.DEBUG if verbose else logging.INFO)
    log_options(options, verbose=verbose)
    try:
        configs = extract_configs(options, validate=([LocalCliConfig]))
        runner = LocalRunner(
            **configs,  # type: ignore
        )
        runner.run(**options)
    except Exception as e:
        logger.error(e, exc_info=True)
        raise click.ClickException(str(e)) from e


def get_source_cmd() -> click.Group:
    cmd = local_source
    add_options(cmd, extras=[LocalCliConfig, CliRecursiveConfig])
    return cmd
