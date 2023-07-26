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
    "--authority-url",
    default="https://login.microsoftonline.com",
    help="Authentication token provider for Microsoft apps, default is "
    "https://login.microsoftonline.com",
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
@click.option(
    "--user-email",
    default=None,
    help="Outlook email to download messages from.",
)
@click.option(
    "--outlook-folders",
    default=None,
    help="Comma separated list of folders to download email messages from. "
    "Do not specify subfolders. Use quotes if spaces in folder names.",
)
@click.option(
    "--user-email",
    required=True,
    help="Outlook email to download messages from.",
)
@click.option(
    "--outlook-folders",
    default=None,
    help="Comma separated list of folders to download email messages from. "
    "Do not specify subfolders. Use quotes if spaces in folder names.",
)
@click.option(
    "--recursive",
    is_flag=True,
    default=False,
    help="Recursively download files in their respective folders"
    "otherwise stop at the files in provided folder level.",
)
def outlook(
    ctx,
    client_id,
    client_cred,
    authority_url,
    tenant,
    user_email,
    outlook_folders,
    recursive,
):
    context_dict = ctx.obj
    ingest_log_streaming_init(logging.DEBUG if context_dict["verbose"] else logging.INFO)

    logger.debug(f"parent params: {context_dict}")
    logger.debug(
        "params: {}".format(
            {
                "client_id": client_id,
                "client_cred": client_cred,
                "authority_url": authority_url,
                "tenant": tenant,
                "user_email": user_email,
                "outlook_folders": outlook_folders,
                "recursive": recursive,
            },
        ),
    )
    hashed_dir_name = hashlib.sha256(user_email.encode("utf-8"))
    update_download_dir_hash(ctx_dict=context_dict, hashed_dir_name=hashed_dir_name, logger=logger)

    from unstructured.ingest.connector.outlook import (
        OutlookConnector,
        SimpleOutlookConfig,
    )

    doc_connector = OutlookConnector(  # type: ignore
        standard_config=map_to_standard_config(context_dict),
        config=SimpleOutlookConfig(
            client_id=client_id,
            client_credential=client_cred,
            user_email=user_email,
            tenant=tenant,
            authority_url=authority_url,
            ms_outlook_folders=SimpleOutlookConfig.parse_folders(outlook_folders),
            recursive=recursive,
        ),
    )

    process_documents(doc_connector=doc_connector, ctx_dict=context_dict)
