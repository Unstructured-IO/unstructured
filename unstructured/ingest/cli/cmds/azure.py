import logging

import click
from click import ClickException

from unstructured.ingest.cli.common import (
    log_options,
    map_to_standard_config,
    process_documents,
    run_init_checks,
    update_download_dir_remote_url,
)
from unstructured.ingest.logger import ingest_log_streaming_init, logger


@click.command()
@click.option(
    "--account-key",
    default=None,
    help="Azure Blob Storage or DataLake account key (not required if "
    "`azure_account_name` is public).",
)
@click.option(
    "--account-name",
    default=None,
    help="Azure Blob Storage or DataLake account name.",
)
@click.option(
    "--connection-string",
    default=None,
    help="Azure Blob Storage or DataLake connection string.",
)
def azure(**options):
    run_init_checks(options=options)
    ingest_log_streaming_init(logging.DEBUG if options["verbose"] else logging.INFO)
    log_options(options=options)

    if not options["account_name"] and not options["connection_string"]:
        raise ClickException(
            "missing either --account-name or --connection-string",
        )

    update_download_dir_remote_url(options=options, remote_url=options["remote_url"], logger=logger)

    from unstructured.ingest.connector.azure import (
        AzureBlobStorageConnector,
        SimpleAzureBlobStorageConfig,
    )

    if options["account_name"]:
        access_kwargs = {
            "account_name": options["account_name"],
            "account_key": options["account_key"],
        }
    elif options["connection_string"]:
        access_kwargs = {"connection_string": options["connection_string"]}
    else:
        access_kwargs = {}
    doc_connector = AzureBlobStorageConnector(  # type: ignore
        standard_config=map_to_standard_config(options=options),
        config=SimpleAzureBlobStorageConfig(
            path=options["remote_url"],
            recursive=options["recursive"],
            access_kwargs=access_kwargs,
        ),
    )

    process_documents(doc_connector=doc_connector, options=options)
