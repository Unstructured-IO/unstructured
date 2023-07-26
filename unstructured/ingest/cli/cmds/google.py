import logging

import click

from unstructured.ingest.cli.common import (
    map_to_standard_config,
    process_documents,
    update_download_dir,
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
    "--gcs-token",
    default=None,
    help="Token used to access Google Cloud. GCSFS will attempt to use your default gcloud creds"
    "or get creds from the google metadata service or fall back to anonymous access.",
)
def google(ctx, remote_url, recursive, gcs_token):
    context_dict = ctx.obj
    ingest_log_streaming_init(logging.DEBUG if context_dict["verbose"] else logging.INFO)

    logger.debug(f"parent params: {context_dict}")
    logger.debug(
        "params: {}".format(
            {
                "remote_url": remote_url,
                "recursive": recursive,
                "gcs_token": gcs_token,
            },
        ),
    )

    update_download_dir(ctx_dict=context_dict, remote_url=remote_url, logger=logger)

    from unstructured.ingest.connector.gcs import GcsConnector, SimpleGcsConfig

    doc_connector = GcsConnector(  # type: ignore
        standard_config=map_to_standard_config(context_dict),
        config=SimpleGcsConfig(
            path=remote_url,
            recursive=recursive,
            access_kwargs={"token": gcs_token},
        ),
    )

    process_documents(doc_connector=doc_connector, ctx_dict=context_dict)
