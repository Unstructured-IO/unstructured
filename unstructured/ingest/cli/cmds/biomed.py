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
    "--decay",
    default=0.3,
    help="(In float) Factor to multiply the delay between retries.",
)
@click.option(
    "--path",
    default=None,
    help="PMC Open Access FTP Directory Path.",
)
@click.option(
    "--max-request-time",
    default=45,
    help="(In seconds) Max request time to OA Web Service API.",
)
@click.option(
    "--max-retries",
    default=1,
    help="Max requests to OA Web Service API.",
)
def biomed(
    **options,
):
    run_init_checks(options=options)
    ingest_log_streaming_init(logging.DEBUG if options["verbose"] else logging.INFO)
    log_options(options=options)

    base_path = options["path"]
    if not options["path"]:
        base_path = "{}-{}-{}".format(
            options.get("api_id", ""),
            options.get("api_from", ""),
            options.get("api_until", ""),
        )
    hashed_dir_name = hashlib.sha256(
        base_path.encode("utf-8"),
    )

    update_download_dir_hash(options=options, hashed_dir_name=hashed_dir_name, logger=logger)

    from unstructured.ingest.connector.biomed import (
        BiomedConnector,
        SimpleBiomedConfig,
    )

    doc_connector = BiomedConnector(  # type: ignore
        standard_config=map_to_standard_config(options=options),
        config=SimpleBiomedConfig(
            path=options["path"],
            id_=options["api_id"],
            from_=options["api_from"],
            until=options["api_until"],
            max_retries=options["max_retries"],
            request_timeout=options["max_request_time"],
            decay=options["decay"],
        ),
    )

    process_documents(doc_connector=doc_connector, options=options)
