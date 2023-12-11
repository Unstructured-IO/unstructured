import typing as t
from dataclasses import dataclass

import click

from unstructured.ingest.cli.base.src import BaseSrcCmd
from unstructured.ingest.cli.interfaces import (
    CliConfig,
)
from unstructured.ingest.connector.fsspec.s3 import S3WriteConfig, SimpleS3Config

CMD_NAME = "s3"


@dataclass
class S3CliConfig(SimpleS3Config, CliConfig):
    @staticmethod
    def get_cli_options() -> t.List[click.Option]:
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


def get_base_src_cmd():
    cmd_cls = BaseSrcCmd(
        cmd_name=CMD_NAME,
        cli_config=S3CliConfig,
        is_fsspec=True,
    )
    return cmd_cls


def get_base_dest_cmd():
    from unstructured.ingest.cli.base.dest import BaseDestCmd

    cmd_cls = BaseDestCmd(
        cmd_name=CMD_NAME,
        cli_config=S3CliConfig,
        write_config=S3WriteConfig,
        is_fsspec=True,
    )
    return cmd_cls
