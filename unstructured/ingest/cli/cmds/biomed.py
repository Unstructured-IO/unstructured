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
    "--biomed-path",
    default=None,
    help="PMC Open Access FTP Directory Path.",
)
@click.option(
    "--biomed-api-id",
    default=None,
    help="ID parameter for OA Web Service API.",
)
@click.option(
    "--biomed-api-from",
    default=None,
    help="From parameter for OA Web Service API.",
)
@click.option(
    "--biomed-api-until",
    default=None,
    help="Until parameter for OA Web Service API.",
)
@click.option(
    "--biomed-max-retries",
    default=1,
    help="Max requests to OA Web Service API.",
)
@click.option(
    "--biomed-max-request-time",
    default=45,
    help="(In seconds) Max request time to OA Web Service API.",
)
@click.option(
    "--biomed-decay",
    default=0.3,
    help="(In float) Factor to multiply the delay between retries.",
)
def biomed(
    ctx,
    biomed_path,
    biomed_api_id,
    biomed_api_from,
    biomed_api_until,
    biomed_max_retries,
    biomed_max_request_time,
    biomed_decay,
):
    context_dict = ctx.obj
    ingest_log_streaming_init(logging.DEBUG if context_dict["verbose"] else logging.INFO)

    logger.debug(f"parent params: {context_dict}")
    logger.debug(
        "params: {}".format(
            {
                "biomed_path": biomed_path,
                "biomed_api_id": biomed_api_id,
                "biomed_api_from": biomed_api_from,
                "biomed_api_until": biomed_api_until,
                "biomed_max_retries": biomed_max_retries,
                "biomed_max_request_time": biomed_max_request_time,
                "biomed_decay": biomed_decay,
            },
        ),
    )
    base_path = biomed_path
    if not biomed_path:
        base_path = f"{biomed_api_id or ''}-{biomed_api_from or ''}-" f"{biomed_api_until or ''}"
    hashed_dir_name = str(
        hashlib.sha256(
            base_path.encode("utf-8"),
        ),
    )
    update_download_dir_hash(ctx_dict=context_dict, hashed_dir_name=hashed_dir_name, logger=logger)

    from unstructured.ingest.connector.biomed import (
        BiomedConnector,
        SimpleBiomedConfig,
    )

    doc_connector = BiomedConnector(  # type: ignore
        standard_config=map_to_standard_config(context_dict),
        config=SimpleBiomedConfig(
            path=biomed_path,
            id_=biomed_api_id,
            from_=biomed_api_from,
            until=biomed_api_until,
            max_retries=biomed_max_retries,
            request_timeout=biomed_max_request_time,
            decay=biomed_decay,
        ),
    )

    process_documents(doc_connector=doc_connector, ctx_dict=context_dict)
