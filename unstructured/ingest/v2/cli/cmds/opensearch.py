from dataclasses import dataclass

import click

from unstructured.ingest.v2.cli.base import DestCmd, SrcCmd
from unstructured.ingest.v2.cli.cmds.elasticsearch import (
    ElasticsearchCliDownloadConfig,
    ElasticsearchCliIndexerConfig,
    ElasticsearchCliUploadStagerConfig,
    ElasticsearchUploaderConfig,
)
from unstructured.ingest.v2.cli.interfaces import CliConfig
from unstructured.ingest.v2.cli.utils import DelimitedString
from unstructured.ingest.v2.processes.connectors.opensearch import CONNECTOR_TYPE


@dataclass
class OpenSearchCliConnectionConfig(CliConfig):
    @staticmethod
    def get_cli_options() -> list[click.Option]:
        options = [
            click.Option(
                ["--hosts"],
                type=DelimitedString(),
                help='List of the OpenSearch hosts to connect to, e.g. "http://localhost:9200"',
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
        ]
        return options


opensearch_src_cmd = SrcCmd(
    cmd_name=CONNECTOR_TYPE,
    connection_config=OpenSearchCliConnectionConfig,
    indexer_config=ElasticsearchCliIndexerConfig,
    downloader_config=ElasticsearchCliDownloadConfig,
)

opensearch_dest_cmd = DestCmd(
    cmd_name=CONNECTOR_TYPE,
    connection_config=OpenSearchCliConnectionConfig,
    upload_stager_config=ElasticsearchCliUploadStagerConfig,
    uploader_config=ElasticsearchUploaderConfig,
)
