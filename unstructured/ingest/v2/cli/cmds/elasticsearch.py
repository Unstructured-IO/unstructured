from dataclasses import dataclass

import click

from unstructured.ingest.v2.cli.base import DestCmd, SrcCmd
from unstructured.ingest.v2.cli.interfaces import CliConfig
from unstructured.ingest.v2.cli.utils import DelimitedString
from unstructured.ingest.v2.processes.connectors.elasticsearch import CONNECTOR_TYPE


@dataclass
class ElasticsearchCliConnectionConfig(CliConfig):
    @staticmethod
    def get_cli_options() -> list[click.Option]:
        options = [
            click.Option(
                ["--hosts"],
                type=DelimitedString(),
                help='List of the Elasticsearch hosts to connect to, e.g. "http://localhost:9200"',
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
                "https://www.elastic.co/guide/en/elasticsearch/reference/current/security-api-create-api-key.html",  # noqa: E501
                # noqa: E501
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
        ]
        return options


@dataclass
class ElasticsearchCliDownloadConfig(CliConfig):
    @staticmethod
    def get_cli_options() -> list[click.Option]:
        options = [
            click.Option(
                ["--download-dir"],
                help="Where files are downloaded to, defaults to a location at"
                "`$HOME/.cache/unstructured/ingest/<connector name>/<SHA256>`.",
            ),
            click.Option(
                ["--fields"],
                type=DelimitedString(),
                default=[],
                help="If provided, will limit the fields returned by Elasticsearch "
                "to this comma-delimited list",
            ),
        ]
        return options


@dataclass
class ElasticsearchCliIndexerConfig(CliConfig):
    @staticmethod
    def get_cli_options() -> list[click.Option]:
        options = [
            click.Option(
                ["--index-name"],
                required=True,
                type=str,
                help="Name of the Elasticsearch index to pull data from, or upload data to.",
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
class ElasticsearchCliUploadStagerConfig(CliConfig):
    @staticmethod
    def get_cli_options() -> list[click.Option]:
        options = [
            click.Option(
                ["--index-name"],
                required=True,
                type=str,
                help="Name of the Elasticsearch index to pull data from, or upload data to.",
            ),
        ]
        return options


@dataclass
class ElasticsearchUploaderConfig(CliConfig):
    @staticmethod
    def get_cli_options() -> list[click.Option]:
        options = [
            click.Option(
                ["--batch-size-bytes"],
                required=False,
                default=15_000_000,
                type=int,
                help="Size limit (in bytes) for each batch of items to be uploaded. Check"
                " https://www.elastic.co/guide/en/elasticsearch/guide/current/bulk.html"
                "#_how_big_is_too_big for more information.",
            ),
            click.Option(
                ["--num-threads"],
                required=False,
                default=1,
                type=int,
                help="Number of threads to be used while uploading content",
            ),
        ]
        return options


elasticsearch_src_cmd = SrcCmd(
    cmd_name=CONNECTOR_TYPE,
    connection_config=ElasticsearchCliConnectionConfig,
    indexer_config=ElasticsearchCliIndexerConfig,
    downloader_config=ElasticsearchCliDownloadConfig,
)

elasticsearch_dest_cmd = DestCmd(
    cmd_name=CONNECTOR_TYPE,
    connection_config=ElasticsearchCliConnectionConfig,
    upload_stager_config=ElasticsearchCliUploadStagerConfig,
    uploader_config=ElasticsearchUploaderConfig,
)
