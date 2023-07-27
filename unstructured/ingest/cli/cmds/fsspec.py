import logging
import warnings
from urllib.parse import urlparse

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
def fsspec(**options):
    fsspec_fn(**options)


def fsspec_fn(**options):
    run_init_checks(options=options)
    ingest_log_streaming_init(logging.DEBUG if options["verbose"] else logging.INFO)
    log_options(options=options)

    update_download_dir_remote_url(options=options, remote_url=options["remote_url"], logger=logger)

    protocol = urlparse(options["remote_url"]).scheme
    warnings.warn(
        f"`fsspec` protocol {protocol} is not directly supported by `unstructured`,"
        " so use it at your own risk. Supported protocols are `gcs`, `gs`, `s3`, `s3a`,"
        "`dropbox`, `abfs` and `az`.",
        UserWarning,
    )

    from unstructured.ingest.connector.fsspec import (
        FsspecConnector,
        SimpleFsspecConfig,
    )

    doc_connector = FsspecConnector(  # type: ignore
        standard_config=map_to_standard_config(options=options),
        config=SimpleFsspecConfig(
            path=options["remote_url"],
            recursive=options["recursive"],
        ),
    )

    process_documents(doc_connector=doc_connector, options=options)
