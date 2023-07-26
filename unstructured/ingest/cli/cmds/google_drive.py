import hashlib
import logging

import click

from unstructured.ingest.cli.common import (
    map_to_standard_config,
    process_documents,
    update_download_dir_hash,
)
from unstructured.ingest.logger import ingest_log_streaming_init, logger


@click.command()
@click.pass_context
@click.option(
    "--drive-id",
    required=True,
    help="Google Drive File or Folder ID.",
)
@click.option(
    "--drive-service-account-key",
    required=True,
    help="Path to the Google Drive service account json file.",
)
@click.option(
    "--drive-extension",
    default=None,
    help="Filters the files to be processed based on extension e.g. .jpg, .docx, etc.",
)
@click.option(
    "--recursive",
    is_flag=True,
    default=False,
    help="Recursively download files in their respective folders"
    "otherwise stop at the files in provided folder level.",
)
def gdrive(
    ctx,
    drive_id,
    drive_service_account_key,
    drive_extension,
    recursive,
):
    context_dict = ctx.obj
    ingest_log_streaming_init(logging.DEBUG if context_dict["verbose"] else logging.INFO)

    logger.debug(f"parent params: {context_dict}")
    logger.debug(
        "params: {}".format(
            {
                "wikipedia_page_title": drive_id,
                "wikipedia_auto_suggest": drive_service_account_key,
                "drive_extension": drive_extension,
                "recursive": recursive,
            },
        ),
    )
    hashed_dir_name = str(
        hashlib.sha256(
            drive_id.encode("utf-8"),
        ),
    )
    update_download_dir_hash(ctx_dict=context_dict, hashed_dir_name=hashed_dir_name, logger=logger)

    from unstructured.ingest.connector.google_drive import (
        GoogleDriveConnector,
        SimpleGoogleDriveConfig,
    )

    doc_connector = GoogleDriveConnector(  # type: ignore
        standard_config=map_to_standard_config(context_dict),
        config=SimpleGoogleDriveConfig(
            drive_id=drive_id,
            service_account_key=drive_service_account_key,
            recursive=recursive,
            extension=drive_extension,
        ),
    )

    process_documents(doc_connector=doc_connector, ctx_dict=context_dict)
