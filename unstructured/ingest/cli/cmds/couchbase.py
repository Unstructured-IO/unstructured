import typing as t
from dataclasses import dataclass

import click

from unstructured.ingest.cli.interfaces import CliConfig
from unstructured.ingest.connector.couchbase import (
    CouchbaseWriteConfig,
    SimpleCouchbaseConfig,
)

CMD_NAME = "couchbase"


@dataclass
class CouchbaseCliConfig(SimpleCouchbaseConfig, CliConfig):
    @staticmethod
    def get_cli_options() -> t.List[click.Option]:
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
class CouchbaseCliWriteConfig(CouchbaseWriteConfig, CliConfig):
    @staticmethod
    def get_cli_options() -> t.List[click.Option]:
        options = [
            click.Option(
                ["--batch-size"],
                type=int,
                default=50,
                help="No of documents to upload per batch",
            ),
        ]
        return options


def get_base_dest_cmd():
    from unstructured.ingest.cli.base.dest import BaseDestCmd

    cmd_cls = BaseDestCmd(
        cmd_name=CMD_NAME,
        cli_config=CouchbaseCliConfig,
        additional_cli_options=[CouchbaseCliWriteConfig],
        write_config=CouchbaseWriteConfig,
    )
    return cmd_cls


@dataclass
class CouchbaseCliReadConfig(SimpleCouchbaseConfig, CliConfig):
    @staticmethod
    def get_cli_options() -> t.List[click.Option]:
        options = [
            click.Option(
                ["--batch-size"],
                default=50,
                type=int,
                help="Number of records per batch",
            ),
        ]
        return options


def get_base_src_cmd():
    from unstructured.ingest.cli.base.src import BaseSrcCmd

    cmd_cls = BaseSrcCmd(
        cmd_name=CMD_NAME,
        cli_config=CouchbaseCliConfig,
        additional_cli_options=[CouchbaseCliReadConfig],
    )
    return cmd_cls
