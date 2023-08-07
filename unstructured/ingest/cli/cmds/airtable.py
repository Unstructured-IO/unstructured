import logging

import click

from unstructured.ingest.cli.common import (
    add_recursive_option,
    add_shared_options,
    log_options,
    map_to_processor_config,
    map_to_standard_config,
    run_init_checks,
)
from unstructured.ingest.logger import ingest_log_streaming_init, logger
from unstructured.ingest.runner import airtable as airtable_fn


@click.command()
@click.option(
    "--personal-access-token",
    default=None,
    help="Personal access token to authenticate into Airtable. \
        Check https://support.airtable.com/docs/airtable-api-key-deprecation-notice for more info.",
)
@click.option(
    "--list-of-paths",
    default=None,
    help="""List of paths describing the set of locations to ingest data from within Airtable.
    list_of_airtable_paths: path1 path2 path3 ….
    airtable_path: base_id/table_id(optional)/view_id(optional)/
    Here is an example for one list_of_airtable_paths:
        base1/			                → gets all rows and columns within all tables inside base1
        base1/table1            		→ gets all rows and columns within described table
        base1/table1/view1	            → gets the rows and columns that are visible in view1
    Examples to invalid airtable_paths:
        table1          → has to mention base to be valid
        base1/view1     → has to mention table to be valid
    """,
)
def airtable(**options):
    verbose = options.get("verbose", False)
    ingest_log_streaming_init(logging.DEBUG if verbose else logging.INFO)
    log_options(options)
    try:
        run_init_checks(**options)
        connector_config = map_to_standard_config(options)
        processor_config = map_to_processor_config(options)
        airtable_fn(connector_config=connector_config, processor_config=processor_config, **options)
    except Exception as e:
        logger.error(e, exc_info=True)
        raise click.ClickException(str(e)) from e


def get_cmd() -> click.Command:
    cmd = airtable
    add_shared_options(cmd)
    add_recursive_option(cmd)
    return cmd
