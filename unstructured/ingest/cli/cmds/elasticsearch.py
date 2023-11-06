import typing as t
from dataclasses import dataclass

import click

from unstructured.ingest.cli.base.src import BaseSrcCmd
from unstructured.ingest.cli.interfaces import (
    CliConfig,
)


@dataclass
class ElasticsearchCliConfig(CliConfig):
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


def get_base_src_cmd() -> BaseSrcCmd:
    cmd_cls = BaseSrcCmd(cmd_name="elasticsearch", cli_config=ElasticsearchCliConfig)
    return cmd_cls
