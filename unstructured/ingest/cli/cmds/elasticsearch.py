import typing as t
from dataclasses import dataclass

import click

from unstructured.ingest.cli.base.src import BaseSrcCmd
from unstructured.ingest.cli.interfaces import CliConfig, DelimitedString
from unstructured.ingest.connector.elasticsearch import SimpleElasticsearchConfig

CMD_NAME = "elasticsearch"


@dataclass
class ElasticsearchCliConfig(SimpleElasticsearchConfig, CliConfig):
    @staticmethod
    def get_cli_options() -> t.List[click.Option]:
        options = [
            click.Option(
                ["--index-name"],
                required=True,
                type=str,
                help="Name of the Elasticsearch index to pull data from, or upload data to.",
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


@dataclass
class ElasticsearchCliWriteConfig(CliConfig):
    batch_size: t.Optional[str] = None

    @staticmethod
    def get_cli_options() -> t.List[click.Option]:
        options = [
            click.Option(
                ["--batch-size"],
                required=True,
                default=10,
                type=str,
                help="Number of items to be uploaded each time",
            ),
        ]
        return options


def get_base_src_cmd() -> BaseSrcCmd:
    cmd_cls = BaseSrcCmd(cmd_name=CMD_NAME, cli_config=ElasticsearchCliConfig)
    return cmd_cls


def get_base_dest_cmd():
    from unstructured.ingest.cli.base.dest import BaseDestCmd

    cmd_cls = BaseDestCmd(
        cmd_name=CMD_NAME,
        cli_config=ElasticsearchCliConfig,
        additional_cli_options=[ElasticsearchCliWriteConfig],
    )
    return cmd_cls
