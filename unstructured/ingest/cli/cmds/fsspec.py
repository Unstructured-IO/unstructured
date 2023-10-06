import logging

import click

from unstructured.ingest.cli.common import (
    log_options,
)
from unstructured.ingest.cli.interfaces import (
    CliFilesStorageConfig,
)
from unstructured.ingest.interfaces import (
    FsspecConfig,
)
from unstructured.ingest.cli.interfaces import CliMixin
from unstructured.ingest.cli.utils import Group, add_options, conform_click_options, extract_configs
from unstructured.ingest.connector.fsspec import FsspecWriteConfig
from unstructured.ingest.logger import ingest_log_streaming_init, logger
from unstructured.ingest.runner import FsspecRunner


class FsspecCliWriteConfigs(FsspecWriteConfig, CliMixin):
    """
    filename: t.Optional[str] = None
    indent: int = 4
    encoding: str = "utf-8"
    """

    @staticmethod
    def add_cli_options(cmd: click.Command) -> None:
        options = [
            click.Option(
                ["--filename"],
                default=None,
                type=str,
                help="When uploading a single file to s3, what the filename should be. "
                "Can be omitted if the remote path set contains the filename",
            ),
            click.Option(
                ["--indent"],
                type=int,
                default=4,
                help="What indent to use if the content needs to be converted to json. "
                "Only applies when writing a list of elements.",
            ),
            click.Option(
                ["--encoding"],
                type=str,
                default="utf-8",
                help="what encoding to use when writing the contents to a file. "
                "Only applies when writing a list of elements.",
            ),
        ]
        cmd.params.extend(options)


@click.group(name="fsspec", invoke_without_command=True, cls=Group)
@click.pass_context
def fsspec_source(ctx: click.Context, **options):
    if ctx.invoked_subcommand:
        return

    conform_click_options(options)
    verbose = options.get("verbose", False)
    ingest_log_streaming_init(logging.DEBUG if verbose else logging.INFO)
    log_options(options, verbose=verbose)
    try:
        configs = extract_configs(options, extras={"fsspec_config": FsspecConfig})
        runner = FsspecRunner(
            **configs,  # type: ignore
        )
        runner.run(**options)
    except Exception as e:
        logger.error(e, exc_info=True)
        raise click.ClickException(str(e)) from e


def get_source_cmd() -> click.Group:
    cmd = fsspec_source
    add_options(cmd, extras=[CliFilesStorageConfig])
    return cmd
