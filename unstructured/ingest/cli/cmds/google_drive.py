import logging
import typing as t
from dataclasses import dataclass

import click

from unstructured.ingest.cli.cmds.utils import Group, conform_click_options
from unstructured.ingest.cli.common import (
    log_options,
)
from unstructured.ingest.cli.interfaces import (
    CliMixin,
    CliPartitionConfig,
    CliReadConfig,
    CliRecursiveConfig,
)
from unstructured.ingest.interfaces import BaseConfig
from unstructured.ingest.logger import ingest_log_streaming_init, logger
from unstructured.ingest.runner import gdrive as gdrive_fn


@dataclass
class GoogleDriveCliConfig(BaseConfig, CliMixin):
    drive_id: str
    service_account_key: str
    extension: t.Optional[str] = None

    @staticmethod
    def add_cli_options(cmd: click.Command) -> None:
        options = [
            click.Option(
                ["--drive-id"],
                required=True,
                type=str,
                help="Google Drive File or Folder ID.",
            ),
            click.Option(
                ["--service-account-key"],
                required=True,
                type=str,
                help="Path to the Google Drive service account json file.",
            ),
            click.Option(
                ["--extension"],
                default=None,
                type=str,
                help="Filters the files to be processed based on extension e.g. .jpg, .docx, etc.",
            ),
        ]
        cmd.params.extend(options)


@click.group(name="google-drive", invoke_without_command=True, cls=Group)
@click.pass_context
def google_drive_source(ctx: click.Context, **options):
    if ctx.invoked_subcommand:
        return

    conform_click_options(options)
    verbose = options.get("verbose", False)
    ingest_log_streaming_init(logging.DEBUG if verbose else logging.INFO)
    log_options(options, verbose=verbose)
    try:
        # run_init_checks(**options)
        read_config = CliReadConfig.from_dict(options)
        partition_config = CliPartitionConfig.from_dict(options)
        # Run for schema validation
        GoogleDriveCliConfig.from_dict(options)
        gdrive_fn(read_config=read_config, partition_config=partition_config, **options)
    except Exception as e:
        logger.error(e, exc_info=True)
        raise click.ClickException(str(e)) from e


def get_source_cmd() -> click.Group:
    cmd = google_drive_source
    GoogleDriveCliConfig.add_cli_options(cmd)
    CliRecursiveConfig.add_cli_options(cmd)

    # Common CLI configs
    CliReadConfig.add_cli_options(cmd)
    CliPartitionConfig.add_cli_options(cmd)
    cmd.params.append(click.Option(["-v", "--verbose"], is_flag=True, default=False))
    return cmd
