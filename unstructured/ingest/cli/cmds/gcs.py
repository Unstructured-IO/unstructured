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
    CliRemoteUrlConfig,
)
from unstructured.ingest.cli.utils import Group, add_options, conform_click_options, extract_configs
from unstructured.ingest.interfaces import BaseConfig
from unstructured.ingest.logger import ingest_log_streaming_init, logger
from unstructured.ingest.runner import GCSRunner


@dataclass
class GcsCliConfig(BaseConfig, CliMixin):
    token: t.Optional[str] = None

    @staticmethod
    def add_cli_options(cmd: click.Command) -> None:
        options = [
            click.Option(
                ["--token"],
                default=None,
                help="Token used to access Google Cloud. GCSFS will attempt to use your "
                "default gcloud creds or get creds from the google metadata service "
                "or fall back to anonymous access.",
            ),
        ]
        cmd.params.extend(options)


@click.group(name="gcs", invoke_without_command=True, cls=Group)
@click.pass_context
def gcs_source(ctx: click.Context, **options):
    if ctx.invoked_subcommand:
        return

    conform_click_options(options)
    verbose = options.get("verbose", False)
    ingest_log_streaming_init(logging.DEBUG if verbose else logging.INFO)
    log_options(options, verbose=verbose)
    try:
        configs = extract_configs(options, validate=([GcsCliConfig]))
        runner = GCSRunner(
            **configs,  # type: ignore
        )
        runner.run(**options)
    except Exception as e:
        logger.error(e, exc_info=True)
        raise click.ClickException(str(e)) from e


def get_source_cmd() -> click.Group:
    cmd = gcs_source
    add_options(cmd, extras=[GcsCliConfig, CliRemoteUrlConfig, CliRecursiveConfig])
    return cmd
