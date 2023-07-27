import logging

import click

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
    "--recursive",
    is_flag=True,
    default=False,
    help="Recursively download files in their respective folders"
    "otherwise stop at the files in provided folder level."
    " Supported protocols are: `gcs`, `gs`,",
)
@click.option(
    "--remote-url",
    required=True,
    help="Remote fsspec URL formatted as `protocol://dir/path`, it can contain both "
    "a directory or a single file. Supported protocols are: `gcs`, `gs`,",
)
@click.option(
    "--token",
    required=True,
    help="Token used to access Google Cloud. GCSFS will attempt to use your default gcloud creds"
    "or get creds from the google metadata service or fall back to anonymous access.",
)
def gcs(**options):
    run_init_checks(options=options)
    ingest_log_streaming_init(logging.DEBUG if options["verbose"] else logging.INFO)
    log_options(options=options)

    update_download_dir_remote_url(options=options, remote_url=options["remote_url"], logger=logger)

    from unstructured.ingest.connector.gcs import GcsConnector, SimpleGcsConfig

    doc_connector = GcsConnector(  # type: ignore
        standard_config=map_to_standard_config(options=options),
        config=SimpleGcsConfig(
            path=options["remote_url"],
            recursive=options["recursive"],
            access_kwargs={"token": options["token"]},
        ),
    )

    process_documents(doc_connector=doc_connector, options=options)
