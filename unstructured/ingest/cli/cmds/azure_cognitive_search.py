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
from unstructured.ingest.cli.utils import conform_click_options, orchestrate_runner
from unstructured.ingest.interfaces import BaseConfig
from unstructured.ingest.logger import ingest_log_streaming_init, logger

pass


@dataclass
class AzureCognitiveSearchCliWriteConfig(BaseConfig, CliMixin):
    key: str
    endpoint: str
    index: str

    @staticmethod
    def get_cli_options() -> t.List[click.Option]:
        options = [
            click.Option(
                ["--key"],
                required=True,
                type=str,
                help="Key credential used for authenticating to an Azure service.",
                envvar="AZURE_SEARCH_API_KEY",
                show_envvar=True,
            ),
            click.Option(
                ["--endpoint"],
                required=True,
                type=str,
                help="The URL endpoint of an Azure search service. "
                "In the form of https://{{service_name}}.search.windows.net",
                envvar="AZURE_SEARCH_ENDPOINT",
                show_envvar=True,
            ),
            click.Option(
                ["--index"],
                required=True,
                type=str,
                help="The name of the index to connect to",
            ),
        ]
        return options


@click.command(name="azure-cognitive-search")
@click.pass_context
def azure_cognitive_search_dest(ctx: click.Context, **options):
    if not ctx.parent:
        raise click.ClickException("destination command called without a parent")
    if not ctx.parent.info_name:
        raise click.ClickException("parent command missing info name")
    source_cmd = ctx.parent.info_name.replace("-", "_")
    parent_options: dict = ctx.parent.params if ctx.parent else {}
    conform_click_options(options)
    conform_click_options(parent_options)
    verbose = parent_options.get("verbose", False)
    ingest_log_streaming_init(logging.DEBUG if verbose else logging.INFO)
    log_options(parent_options, verbose=verbose)
    log_options(options, verbose=verbose)
    try:
        orchestrate_runner(
            source_cmd=source_cmd,
            writer_type="azure_cognitive_search",
            parent_options=parent_options,
            options=options,
            validate=[AzureCognitiveSearchCliWriteConfig],
        )
    except Exception as e:
        logger.error(e, exc_info=True)
        raise click.ClickException(str(e)) from e


def get_dest_cmd() -> click.Command:
    cmd = azure_cognitive_search_dest
    AzureCognitiveSearchCliWriteConfig.add_cli_options(cmd)
    return cmd
