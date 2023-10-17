import logging
import typing as t
from dataclasses import dataclass

import click

from unstructured.ingest.cli.common import (
    log_options,
)
from unstructured.ingest.cli.interfaces import (
    CliMixin,
)
from unstructured.ingest.cli.utils import Group, add_options, conform_click_options, extract_configs
from unstructured.ingest.interfaces import BaseConfig
from unstructured.ingest.logger import ingest_log_streaming_init, logger
from unstructured.ingest.runner import BiomedRunner


@dataclass
class BiomedCliConfig(BaseConfig, CliMixin):
    api_id: t.Optional[str] = None
    api_from: t.Optional[str] = None
    api_until: t.Optional[str] = None
    path: t.Optional[str] = None
    max_request_time: int = 45

    @staticmethod
    def get_cli_options() -> t.List[click.Option]:
        options = [
            click.Option(
                ["--api-id"],
                default=None,
                help="ID parameter for OA Web Service API.",
            ),
            click.Option(
                ["--api-from"],
                default=None,
                help="From parameter for OA Web Service API.",
            ),
            click.Option(
                ["--api-until"],
                default=None,
                help="Until parameter for OA Web Service API.",
            ),
            click.Option(
                ["--path"],
                default=None,
                help="PMC Open Access FTP Directory Path.",
            ),
            click.Option(
                ["--max-request-time"],
                default=45,
                help="(In seconds) Max request time to OA Web Service API.",
            ),
        ]
        return options


@click.group(name="biomed", invoke_without_command=True, cls=Group)
@click.pass_context
def biomed_source(ctx: click.Context, **options):
    if ctx.invoked_subcommand:
        return

    conform_click_options(options)
    verbose = options.get("verbose", False)
    ingest_log_streaming_init(logging.DEBUG if verbose else logging.INFO)
    log_options(options, verbose=verbose)
    try:
        configs = extract_configs(options, validate=[BiomedCliConfig])
        runner = BiomedRunner(
            **configs,  # type: ignore
        )
        runner.run(**options)
    except Exception as e:
        logger.error(e, exc_info=True)
        raise click.ClickException(str(e)) from e


def get_source_cmd() -> click.Group:
    cmd = biomed_source
    add_options(cmd, extras=[BiomedCliConfig])
    return cmd
