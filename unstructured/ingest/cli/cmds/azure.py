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
    "a directory or a single file. Supported protocols are: `abfs`, `az`,",
)
@click.option(
    "--recursive",
    is_flag=True,
    default=False,
    help="Recursively download files in their respective folders"
    "otherwise stop at the files in provided folder level."
    " Supported protocols are: `abfs`, `az`,",
)
@click.option(
    "--account-name",
    default=None,
    help="Azure Blob Storage or DataLake account name.",
)
@click.option(
    "--account-key",
    default=None,
    help="Azure Blob Storage or DataLake account key (not required if "
    "`azure_account_name` is public).",
)
@click.option(
    "--connection-string",
    default=None,
    help="Azure Blob Storage or DataLake connection string.",
)
def azure(
    ctx,
    remote_url,
    recursive,
    account_name,
    account_key,
    connection_string,
):
    context_dict = ctx.obj
    ingest_log_streaming_init(logging.DEBUG if context_dict["verbose"] else logging.INFO)

    logger.debug(f"parent params: {context_dict}")
    logger.debug(
        "params: {}".format(
            {
                "remote_url": remote_url,
                "recursive": recursive,
                "account_name": account_name,
                "account_key": account_key,
                "connection_string": connection_string,
            },
        ),
    )

    update_download_dir_remote_url(ctx_dict=context_dict, remote_url=remote_url, logger=logger)

    from unstructured.ingest.connector.azure import (
        AzureBlobStorageConnector,
        SimpleAzureBlobStorageConfig,
    )

    if account_name:
        access_kwargs = {
            "account_name": account_name,
            "account_key": account_key,
        }
    elif connection_string:
        access_kwargs = {"connection_string": connection_string}
    else:
        access_kwargs = {}
    doc_connector = AzureBlobStorageConnector(  # type: ignore
        standard_config=map_to_standard_config(context_dict),
        config=SimpleAzureBlobStorageConfig(
            path=remote_url,
            recursive=recursive,
            access_kwargs=access_kwargs,
        ),
    )

    process_documents(doc_connector=doc_connector, ctx_dict=context_dict)
