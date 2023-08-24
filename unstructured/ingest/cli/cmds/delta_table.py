import logging

import click

from unstructured.ingest.cli.common import (
    add_shared_options,
    log_options,
    map_to_processor_config,
    map_to_standard_config,
    run_init_checks,
)
from unstructured.ingest.logger import ingest_log_streaming_init, logger
from unstructured.ingest.runner import delta_table as delta_table_fn
from unstructured.utils import requires_dependencies


@click.command()
@click.option(
    "--table-uri",
    required=True,
    help="the path of the DeltaTable",
)
@click.option(
    "--version",
    default=None,
    type=int,
    help="version of the DeltaTable",
)
@click.option(
    "--storage_options",
    required=False,
    type=str,
    help="a dictionary of the options to use for the storage backend, "
    "format='value1=key1,value2=key2'",
)
@click.option(
    "--without_files",
    is_flag=True,
    default=False,
    help="If set, will load table without tracking files.",
)
@requires_dependencies(["deltalake", "fsspec"], extras="delta-table")
def delta_table(**options):
    verbose = options.get("verbose", False)
    ingest_log_streaming_init(logging.DEBUG if verbose else logging.INFO)
    log_options(options)
    try:
        run_init_checks(**options)
        connector_config = map_to_standard_config(options)
        processor_config = map_to_processor_config(options)
        if storage_options := options.get("storage_options"):
            formatted_storage_options = {
                w.split("=")[0]: w.split("=")[1] for w in storage_options.split(",")
            }
            options["storage_options"] = formatted_storage_options
        delta_table_fn(
            connector_config=connector_config,
            processor_config=processor_config,
            **options,
        )
    except Exception as e:
        logger.error(e, exc_info=True)
        raise click.ClickException(str(e)) from e


def get_cmd() -> click.Command:
    cmd = delta_table
    add_shared_options(cmd)
    return cmd
