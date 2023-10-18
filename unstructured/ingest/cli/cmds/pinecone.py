import logging
from dataclasses import dataclass

import click

from unstructured.ingest.cli.common import (
    log_options,
)
from unstructured.ingest.cli.interfaces import (
    CliMixin,
)
from unstructured.ingest.cli.utils import conform_click_options, extract_configs
from unstructured.ingest.interfaces import BaseConfig
from unstructured.ingest.logger import ingest_log_streaming_init, logger
from unstructured.ingest.runner import runner_map


@dataclass
class PineconeCliWriteConfig(BaseConfig, CliMixin):
    api_key: str
    index_name: str
    environment: str

    @staticmethod
    def add_cli_options(cmd: click.Command) -> None:
        options = [
            click.Option(
                ["--api-key"],
                required=True,
                type=str,
                help="API key used for authenticating to a Pinecone instance.",
                envvar="PINECONE_API_KEY",
                show_envvar=True,
            ),
            click.Option(
                ["--index-name"],
                required=True,
                type=str,
                help="The name of the pinecone index to connect to.",
            ),
            click.Option(
                ["--environment"],
                required=True,
                type=str,
                help="The environment where the index lives. Eg. 'gcp-starter' or 'us-east1-gcp'",
            ),
        ]
        cmd.params.extend(options)


@click.command(name="pinecone")
@click.pass_context
def pinecone_dest(ctx: click.Context, **options):
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
        configs = extract_configs(options, validate=[PineconeCliWriteConfig])
        runner_cls = runner_map[source_cmd]
        # import pdb; pdb.set_trace()
        runner = runner_cls(
            **configs,  # type: ignore
            writer_type="pinecone",
            writer_kwargs=options,
        )
        runner.run(
            **parent_options,
        )
    except Exception as e:
        logger.error(e, exc_info=True)
        raise click.ClickException(str(e)) from e


def get_dest_cmd() -> click.Command:
    cmd = pinecone_dest
    PineconeCliWriteConfig.add_cli_options(cmd)
    return cmd
