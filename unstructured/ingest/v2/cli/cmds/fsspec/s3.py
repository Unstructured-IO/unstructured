from dataclasses import dataclass

import click

from unstructured.ingest.v2.cli.base import DestCmd, SrcCmd
from unstructured.ingest.v2.cli.cmds.fsspec.fsspec import (
    FsspecCliDownloadConfig,
    FsspecCliIndexerConfig,
    FsspecCliUploaderConfig,
)
from unstructured.ingest.v2.cli.interfaces import CliConfig
from unstructured.ingest.v2.processes.connectors.fsspec.s3 import (
    CONNECTOR_TYPE,
)


@dataclass
class S3CliDownloadConfig(FsspecCliDownloadConfig):
    pass


@dataclass
class S3CliIndexerConfig(FsspecCliIndexerConfig):
    pass


@dataclass
class S3CliConnectionConfig(CliConfig):
    @staticmethod
    def get_cli_options() -> list[click.Option]:
        options = [
            click.Option(
                ["--anonymous"],
                is_flag=True,
                default=False,
                help="Connect to s3 without local AWS credentials.",
            ),
            click.Option(
                ["--endpoint-url"],
                type=str,
                default=None,
                help="Use this endpoint_url, if specified. Needed for "
                "connecting to non-AWS S3 buckets.",
            ),
            click.Option(
                ["--key"],
                type=str,
                default=None,
                help="If not anonymous, use this access key ID, if specified. Takes precedence "
                "over `aws_access_key_id` in client_kwargs.",
            ),
            click.Option(
                ["--secret"],
                type=str,
                default=None,
                help="If not anonymous, use this secret access key, if specified.",
            ),
            click.Option(
                ["--token"],
                type=str,
                default=None,
                help="If not anonymous, use this security token, if specified.",
            ),
        ]
        return options


@dataclass
class S3UploaderConfig(FsspecCliUploaderConfig):
    pass


s3_src_cmd = SrcCmd(
    cmd_name=CONNECTOR_TYPE,
    indexer_config=S3CliIndexerConfig,
    connection_config=S3CliConnectionConfig,
    downloader_config=S3CliDownloadConfig,
)

s3_dest_cmd = DestCmd(
    cmd_name=CONNECTOR_TYPE,
    connection_config=S3CliConnectionConfig,
    uploader_config=S3UploaderConfig,
)
