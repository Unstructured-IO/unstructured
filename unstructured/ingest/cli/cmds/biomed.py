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
    "--path",
    default=None,
    help="PMC Open Access FTP Directory Path.",
)
@click.option(
    "--api-id",
    default=None,
    help="ID parameter for OA Web Service API.",
)
@click.option(
    "--api-from",
    default=None,
    help="From parameter for OA Web Service API.",
)
@click.option(
    "--api-until",
    default=None,
    help="Until parameter for OA Web Service API.",
)
@click.option(
    "--max-retries",
    default=1,
    help="Max requests to OA Web Service API.",
)
@click.option(
    "--max-request-time",
    default=45,
    help="(In seconds) Max request time to OA Web Service API.",
)
@click.option(
    "--decay",
    default=0.3,
    help="(In float) Factor to multiply the delay between retries.",
)
def biomed(
    ctx,
    path,
    api_id,
    api_from,
    api_until,
    max_retries,
    max_request_time,
    decay,
):
    context_dict = ctx.obj
    ingest_log_streaming_init(logging.DEBUG if context_dict["verbose"] else logging.INFO)

    logger.debug(f"parent params: {context_dict}")
    logger.debug(
        "params: {}".format(
            {
                "path": path,
                "api_id": api_id,
                "api_from": api_from,
                "api_until": api_until,
                "max_retries": max_retries,
                "max_request_time": max_request_time,
                "decay": decay,
            },
        ),
    )
    base_path = path
    if not path:
        base_path = f"{api_id or ''}-{api_from or ''}-" f"{api_until or ''}"
    hashed_dir_name = hashlib.sha256(
        base_path.encode("utf-8"),
    )

    update_download_dir_hash(ctx_dict=context_dict, hashed_dir_name=hashed_dir_name, logger=logger)

    from unstructured.ingest.connector.biomed import (
        BiomedConnector,
        SimpleBiomedConfig,
    )

    doc_connector = BiomedConnector(  # type: ignore
        standard_config=map_to_standard_config(context_dict),
        config=SimpleBiomedConfig(
            path=path,
            id_=api_id,
            from_=api_from,
            until=api_until,
            max_retries=max_retries,
            request_timeout=max_request_time,
            decay=decay,
        ),
    )

    process_documents(doc_connector=doc_connector, ctx_dict=context_dict)
