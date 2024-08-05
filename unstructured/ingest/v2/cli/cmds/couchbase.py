from dataclasses import dataclass

import click

from unstructured.ingest.v2.cli.base import DestCmd, SrcCmd
from unstructured.ingest.v2.cli.interfaces import CliConfig
from unstructured.ingest.v2.processes.connectors.couchbase import CONNECTOR_TYPE


@dataclass
class CouchbaseCliConnectionConfig(CliConfig):
    @staticmethod
    def get_cli_options() -> list[click.Option]:
        options = [
            click.Option(
                ["--connection-string"],
                required=True,
                type=str,
                help="The connection string of the Couchbase server",
                envvar="CB_CONN_STR",
                show_envvar=True,
            ),
            click.Option(
                ["--username"],
                required=True,
                type=str,
                envvar="CB_USERNAME",
                help="The username for the Couchbase server",
            ),
            click.Option(
                ["--password"],
                type=str,
                required=True,
                envvar="CB_PASSWORD",
                help="The password for the Couchbase server",
            ),
            click.Option(
                ["--bucket"],
                required=True,
                type=str,
                envvar="CB_BUCKET",
                help="The bucket to connect to on the Couchbase server",
            ),
            click.Option(
                ["--scope"],
                required=True,
                type=str,
                envvar="CB_SCOPE",
                help="The scope to connect to on the Couchbase server",
            ),
            click.Option(
                ["--collection"],
                required=True,
                type=str,
                envvar="CB_COLLECTION",
                help="The collection to connect to on the Couchbase server",
            ),
        ]
        return options


@dataclass
class CouchbaseCliUploaderConfig(CliConfig):
    @staticmethod
    def get_cli_options() -> list[click.Option]:
        options = [
            click.Option(
                ["--batch-size"],
                type=int,
                default=50,
                help="No of documents to upload per batch",
            ),
        ]
        return options


@dataclass
class CouchbaseCliUploadStagerConfig(CliConfig):
    @staticmethod
    def get_cli_options() -> list[click.Option]:
        return []


couchbase_dest_cmd = DestCmd(
    cmd_name=CONNECTOR_TYPE,
    connection_config=CouchbaseCliConnectionConfig,
    upload_stager_config=CouchbaseCliUploadStagerConfig,
    uploader_config=CouchbaseCliUploaderConfig,
)


@dataclass
class CouchbaseCliReadConfig(CliConfig):
    @staticmethod
    def get_cli_options() -> list[click.Option]:
        options = [
            click.Option(
                ["--batch-size"],
                default=50,
                type=int,
                help="Number of records per batch",
            ),
        ]
        return options


couchbase_src_cmd = SrcCmd(
    cmd_name=CONNECTOR_TYPE,
    connection_config=CouchbaseCliConnectionConfig,
    indexer_config=CouchbaseCliReadConfig,
)
