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
)
from unstructured.ingest.interfaces import BaseConfig
from unstructured.ingest.logger import ingest_log_streaming_init, logger
from unstructured.ingest.runner import elasticsearch as elasticsearch_fn


@dataclass
class ElasticsearchCliConfig(BaseConfig, CliMixin):
    index_name: str
    url: str
    jq_query: t.Optional[str] = None

    @staticmethod
    def add_cli_options(cmd: click.Command) -> None:
        options = [
            click.Option(
                ["--index-name"],
                required=True,
                type=str,
                help="Name for the Elasticsearch index to pull data from",
            ),
            click.Option(
                ["--url"],
                required=True,
                type=str,
                help='URL to the Elasticsearch cluster, e.g. "http://localhost:9200"',
            ),
            click.Option(
                ["--jq-query"],
                default=None,
                type=str,
                help="JQ query to get and concatenate a subset of the fields from a JSON document. "
                "For a group of JSON documents, it assumes that all of the documents "
                "have the same schema.  Currently only supported for the Elasticsearch connector. "
                "Example: --jq-query '{meta, body}'",
            ),
        ]
        cmd.params.extend(options)


@click.group(name="elasticsearch", invoke_without_command=True, cls=Group)
@click.pass_context
def elasticsearch_source(ctx: click.Context, **options):
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
        ElasticsearchCliConfig.from_dict(options)
        elasticsearch_fn(read_config=read_config, partition_config=partition_config, **options)
    except Exception as e:
        logger.error(e, exc_info=True)
        raise click.ClickException(str(e)) from e


def get_source_cmd() -> click.Group:
    cmd = elasticsearch_source
    ElasticsearchCliConfig.add_cli_options(cmd)

    # Common CLI configs
    CliReadConfig.add_cli_options(cmd)
    CliPartitionConfig.add_cli_options(cmd)
    cmd.params.append(click.Option(["-v", "--verbose"], is_flag=True, default=False))
    return cmd
