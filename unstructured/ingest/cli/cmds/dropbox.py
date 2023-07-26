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
    "--remote-url",
    required=True,
    help="Remote fsspec URL formatted as `protocol://dir/path`, it can contain both "
    "a directory or a single file. Supported protocols are: `gcs`, `gs`,",
)
@click.option(
    "--recursive",
    is_flag=True,
    default=False,
    help="Recursively download files in their respective folders"
    "otherwise stop at the files in provided folder level."
    " Supported protocols are: `gcs`, `gs`,",
)
@click.option(
    "--token",
    required=True,
    help="Dropbox access token.",
)
def dropbox(ctx, remote_url, recursive, token):
    context_dict = ctx.obj
    ingest_log_streaming_init(logging.DEBUG if context_dict["verbose"] else logging.INFO)

    logger.debug(f"parent params: {context_dict}")
    logger.debug(
        "params: {}".format(
            {
                "remote_url": remote_url,
                "recursive": recursive,
                "token": token,
            },
        ),
    )

    update_download_dir_remote_url(ctx_dict=context_dict, remote_url=remote_url, logger=logger)

    from unstructured.ingest.connector.dropbox import (
        DropboxConnector,
        SimpleDropboxConfig,
    )

    doc_connector = DropboxConnector(  # type: ignore
        standard_config=map_to_standard_config(context_dict),
        config=SimpleDropboxConfig(
            path=remote_url,
            recursive=recursive,
            access_kwargs={"token": token},
        ),
    )

    process_documents(doc_connector=doc_connector, ctx_dict=context_dict)
