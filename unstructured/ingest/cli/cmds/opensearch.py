import typing as t
from dataclasses import dataclass

import click

from unstructured.ingest.cli.base.src import BaseSrcCmd
from unstructured.ingest.cli.interfaces import CliConfig, DelimitedString
from unstructured.ingest.connector.opensearch import (
    OpenSearchWriteConfig,
    SimpleOpenSearchConfig,
)

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
                help="password when using basic auth or connecting to a cloud instance",
            ),
            click.Option(
                ["--cloud-id"], type=str, default=None, help="id used to connect to Elastic Cloud"
            ),
            click.Option(
                ["--es-api-key"], type=str, default=None, help="api key used for authentication"
            ),
            click.Option(
                ["--api-key-id"],
                type=str,
                default=None,
                help="id associated with api key used for authentication: "
                "https://www.elastic.co/guide/en/opensearch/reference/current/security-api-create-api-key.html",  # noqa: E501
            ),
            click.Option(
                ["--bearer-auth"],
                type=str,
                default=None,
                help="bearer token used for HTTP bearer authentication",
            ),
            click.Option(
                ["--ca-certs"],
                type=click.Path(),
                default=None,
            ),
            click.Option(
                ["--ssl-assert-fingerprint"],
                type=str,
                default=None,
                help="SHA256 fingerprint value",
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
class OpenSearchCliWriteConfig(OpenSearchWriteConfig, CliConfig):
    @staticmethod
    def get_cli_options() -> t.List[click.Option]:
        options = [
            click.Option(
                ["--batch-size-bytes"],
                required=True,
                default=15_000_000,
                type=int,
                help="Size limit (in bytes) for each batch of items to be uploaded. Check"
                " https://www.elastic.co/guide/en/opensearch/guide/current/bulk.html"
                "#_how_big_is_too_big for more information.",
            ),
            click.Option(
                ["--num-processes"],
                required=True,
                default=2,
                type=int,
                help="Number of processes to be used while uploading content",
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
        additional_cli_options=[OpenSearchCliWriteConfig],
        addition_configs={
            "connector_config": SimpleOpenSearchConfig,
            "write_config": OpenSearchCliWriteConfig,
        },
    )
    return cmd_cls
