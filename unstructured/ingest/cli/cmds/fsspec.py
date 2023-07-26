import logging
import warnings
from urllib.parse import urlparse

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
    "a directory or a single file.",
)
@click.option(
    "--recursive",
    is_flag=True,
    default=False,
    help="Recursively download files in their respective folders"
    "otherwise stop at the files in provided folder level.",
)
def fsspec(ctx, remote_url, recursive):
    context_dict = ctx.obj
    ingest_log_streaming_init(logging.DEBUG if context_dict["verbose"] else logging.INFO)

    logger.debug(f"parent params: {context_dict}")
    logger.debug(
        "params: {}".format(
            {
                "remote_url": remote_url,
                "recursive": recursive,
            },
        ),
    )

    update_download_dir_remote_url(ctx_dict=context_dict, remote_url=remote_url, logger=logger)

    protocol = urlparse(remote_url).scheme
    warnings.warn(
        f"`fsspec` protocol {protocol} is not directly supported by `unstructured`,"
        " so use it at your own risk. Supported protocols are `gcs`, `gs`, `s3`, `s3a`,"
        "`dropbox`, `abfs` and `az`.",
        UserWarning,
    )

    from unstructured.ingest.connector.fsspec import (
        FsspecConnector,
        SimpleFsspecConfig,
    )

    doc_connector = FsspecConnector(  # type: ignore
        standard_config=map_to_standard_config(context_dict),
        config=SimpleFsspecConfig(
            path=remote_url,
            recursive=recursive,
        ),
    )

    process_documents(doc_connector=doc_connector, ctx_dict=context_dict)
