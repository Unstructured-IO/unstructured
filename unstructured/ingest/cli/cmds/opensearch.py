import typing as t
from dataclasses import dataclass

import click

from unstructured.ingest.cli.base.src import BaseSrcCmd
from unstructured.ingest.cli.cmds.elasticsearch import ElasticsearchCliWriteConfig
from unstructured.ingest.cli.interfaces import CliConfig, DelimitedString
from unstructured.ingest.connector.opensearch import SimpleOpenSearchConfig

CMD_NAME = "opensearch"


@dataclass
class OpenSearchCliConfig(SimpleOpenSearchConfig, CliConfig):
    @staticmethod
    def get_cli_options() -> t.List[click.Option]:
        options = [
            click.Option(
                ["--index-name"],
                required=True,
                type=str,
                help="Name of the OpenSearch index to pull data from, or upload data to.",
            ),
            click.Option(
                ["--hosts"],
                type=DelimitedString(),
                help='List of the OpenSearch hosts to connect to, e.g. "http://localhost:9200"',
            ),
            click.Option(
                ["--fields"],
                type=DelimitedString(),
                default=[],
                help="If provided, will limit the fields returned by OpenSearch "
                "to this comma-delimited list",
            ),
            click.Option(
                ["--username"], type=str, default=None, help="username when using basic auth"
            ),
            click.Option(
                ["--password"],
                type=str,
                default=None,
                help="password when using basic auth",
            ),
            click.Option(
                ["--use-ssl"],
                type=bool,
                default=False,
                is_flag=True,
                help="use ssl for the connection",
            ),
            click.Option(
                ["--verify-certs"],
                type=bool,
                default=False,
                is_flag=True,
                help="whether to verify SSL certificates",
            ),
            click.Option(
                ["--ssl-show-warn"],
                type=bool,
                default=False,
                is_flag=True,
                help="show warning when verify certs is disabled",
            ),
            click.Option(
                ["--ca-certs"],
                type=click.Path(),
                default=None,
                help="path to CA bundle",
            ),
            click.Option(
                ["--client-cert"],
                type=click.Path(),
                default=None,
                help="path to the file containing the private key and the certificate,"
                " or cert only if using client_key",
            ),
            click.Option(
                ["--client-key"],
                type=click.Path(),
                default=None,
                help="path to the file containing the private key"
                " if using separate cert and key files",
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
    cmd_cls = BaseSrcCmd(
        cmd_name="opensearch",
        cli_config=OpenSearchCliConfig,
    )
    return cmd_cls


def get_base_dest_cmd():
    from unstructured.ingest.cli.base.dest import BaseDestCmd

    cmd_cls = BaseDestCmd(
        cmd_name="opensearch",
        cli_config=OpenSearchCliConfig,
        additional_cli_options=[ElasticsearchCliWriteConfig],
        addition_configs={
            "connector_config": SimpleOpenSearchConfig,
            "write_config": ElasticsearchCliWriteConfig,
        },
    )
    return cmd_cls
