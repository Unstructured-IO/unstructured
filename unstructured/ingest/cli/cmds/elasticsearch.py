import typing as t
from dataclasses import dataclass

import click

from unstructured.ingest.cli.base.src import BaseSrcCmd
from unstructured.ingest.cli.interfaces import CliConfig, DelimitedString
from unstructured.ingest.connector.elasticsearch import SimpleElasticsearchConfig


@dataclass
class ElasticsearchCliConfig(SimpleElasticsearchConfig, CliConfig):
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
                ["--fields"],
                type=DelimitedString(),
                default=[],
                help="If provided, will limit the fields returned by Elasticsearch "
                "to this comma-delimited list",
            ),
            click.Option(
                ["--batch-size"],
                default=100,
                type=click.IntRange(0),
                help="how many records to read at a time per process",
            ),
        ]
        return options


def get_base_src_cmd() -> BaseSrcCmd:
    cmd_cls = BaseSrcCmd(cmd_name="elasticsearch", cli_config=ElasticsearchCliConfig)
    return cmd_cls
