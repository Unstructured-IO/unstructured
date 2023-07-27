import hashlib
import logging

import click

from unstructured.ingest.cli.common import (
    log_options,
    map_to_standard_config,
    process_documents,
    run_init_checks,
    update_download_dir_hash,
)
from unstructured.ingest.logger import ingest_log_streaming_init, logger


@click.command()
@click.pass_context
@click.option(
    "--id",
    required=True,
    help="Google Drive File or Folder ID.",
)
@click.option(
    "--extension",
    default=None,
    help="Filters the files to be processed based on extension e.g. .jpg, .docx, etc.",
)
@click.option(
    "--service-account-key",
    required=True,
    help="Path to the Google Drive service account json file.",
)
def gdrive(**options):
    gdrive_fn(**options)


def gdrive_fn(**options):
    run_init_checks(options=options)
    ingest_log_streaming_init(logging.DEBUG if options["verbose"] else logging.INFO)
    log_options(options=options)

    hashed_dir_name = hashlib.sha256(
        options["id"].encode("utf-8"),
    )
    update_download_dir_hash(options=options, hashed_dir_name=hashed_dir_name, logger=logger)

    from unstructured.ingest.connector.google_drive import (
        GoogleDriveConnector,
        SimpleGoogleDriveConfig,
    )

    doc_connector = GoogleDriveConnector(  # type: ignore
        standard_config=map_to_standard_config(options=options),
        config=SimpleGoogleDriveConfig(
            drive_id=options["id"],
            service_account_key=options["service_account_key"],
            recursive=options["recursive"],
            extension=options["extension"],
        ),
    )

    process_documents(doc_connector=doc_connector, options=options)
