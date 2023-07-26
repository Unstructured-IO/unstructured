import logging

import click

from unstructured.ingest.cli.common import (
    map_to_standard_config,
    process_documents,
    update_download_dir_remote_url,
)
from unstructured.ingest.logger import ingest_log_streaming_init, logger


@click.command()
@click.pass_context
@click.option(
    "--anonymous",
    is_flag=True,
    default=False,
    help="Connect to s3 without local AWS credentials.",
)
@click.option(
    "--remote-url",
    required=True,
    help="Remote fsspec URL formatted as `protocol://dir/path`, it can contain both "
    "a directory or a single file. Supported protocols are: `s3`, `s3a`",
)
@click.option(
    "--recursive",
    is_flag=True,
    default=False,
    help="Recursively download files in their respective folders"
    "otherwise stop at the files in provided folder level."
    " Supported protocols are: `s3`, `s3a`",
)
def s3(ctx, anonymous, remote_url, recursive):
    context_dict = ctx.obj
    ingest_log_streaming_init(logging.DEBUG if context_dict["verbose"] else logging.INFO)

    logger.debug(f"parent params: {context_dict}")
    logger.debug(
        "params: {}".format(
            {
                "anonymous": anonymous,
                "remote_url": remote_url,
                "recursive": recursive,
            },
        ),
    )

    update_download_dir_remote_url(ctx_dict=context_dict, remote_url=remote_url, logger=logger)

    from unstructured.ingest.connector.s3 import S3Connector, SimpleS3Config

    doc_connector = S3Connector(  # type: ignore
        standard_config=map_to_standard_config(context_dict),
        config=SimpleS3Config(
            path=remote_url,
            recursive=recursive,
            access_kwargs={"anon": anonymous},
        ),
    )

    process_documents(doc_connector=doc_connector, ctx_dict=context_dict)
