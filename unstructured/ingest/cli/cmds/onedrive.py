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
@click.option(
    "--authority-url",
    default="https://login.microsoftonline.com",
    help="Authentication token provider for Microsoft apps, default is "
    "https://login.microsoftonline.com",
)
@click.option(
    "--client-id",
    required=True,
    help="Microsoft app client ID",
)
@click.option(
    "--client-cred",
    default=None,
    help="Microsoft App client secret",
)
@click.option(
    "--onedrive-folder",
    default=None,
    help="Folder to start parsing files from.",
)
@click.option(
    "--tenant",
    default="common",
    help="ID or domain name associated with your Azure AD instance",
)
@click.option(
    "--user-pname",
    required=True,
    help="User principal name, usually is your Azure AD email.",
)
def onedrive(**options):
    run_init_checks(options=options)
    ingest_log_streaming_init(logging.DEBUG if options["verbose"] else logging.INFO)
    log_options(options=options)

    hashed_dir_name = hashlib.sha256(
        "{tenant}_{user_pname}".format(
            tenant=options["tenant"],
            user_pname=options["user_pname"],
        ).encode("utf-8"),
    )
    update_download_dir_hash(options=options, hashed_dir_name=hashed_dir_name, logger=logger)

    from unstructured.ingest.connector.onedrive import (
        OneDriveConnector,
        SimpleOneDriveConfig,
    )

    doc_connector = OneDriveConnector(  # type: ignore
        standard_config=map_to_standard_config(options=options),
        config=SimpleOneDriveConfig(
            client_id=options["client_id"],
            client_credential=options["client_cred"],
            user_pname=options["user_pname"],
            tenant=options["tenant"],
            authority_url=options["authority_url"],
            folder=options["onedrive_folder"],
            recursive=options["recursive"],
        ),
    )

    process_documents(doc_connector=doc_connector, options=options)
