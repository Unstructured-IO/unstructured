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
from unstructured.ingest.runner import ElasticSearchRunner


@dataclass
class ElasticsearchCliConfig(BaseConfig, CliMixin):
    index_name: str
    url: str
    jq_query: t.Optional[str] = None

    @staticmethod
    def get_cli_options() -> t.List[click.Option]:
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
        return options


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
        configs = extract_configs(options, validate=[ElasticsearchCliConfig])
        runner = ElasticSearchRunner(
            **configs,  # type: ignore
        )
        runner.run(**options)
    except Exception as e:
        logger.error(e, exc_info=True)
        raise click.ClickException(str(e)) from e


def get_source_cmd() -> click.Group:
    cmd = elasticsearch_source
    add_options(cmd, extras=[ElasticsearchCliConfig])
    return cmd
