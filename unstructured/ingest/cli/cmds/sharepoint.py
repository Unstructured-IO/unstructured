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
from unstructured.ingest.runner import sharepoint as sharepoint_fn


@click.command()
@click.option(
    "--client-id",
    default=None,
    help="Sharepoint app client ID",
)
@click.option(
    "--client-cred",
    default=None,
    help="Sharepoint app secret",
)
@click.option(
    "--site",
    default=None,
    help="Sharepoint site url. Process either base url e.g https://[tenant].sharepoint.com \
        or relative sites https://[tenant].sharepoint.com/sites/<site_name>.\
        To process all sites within the tenant pass a site url as\
        https://[tenant]-admin.sharepoint.com.\
        This requires the app to be registered at a tenant level",
)
@click.option(
    "--path",
    default="Shared Documents",
    help="Path from which to start parsing files. If the connector is to process all sites \
    within the tenant this filter will be applied to all sites document libraries. \
    Default 'Shared Documents'",
)
@click.option(
    "--files-only",
    is_flag=True,
    default=False,
    help="Process only files.",
)
def sharepoint(**options):
    verbose = options.get("verbose", False)
    ingest_log_streaming_init(logging.DEBUG if verbose else logging.INFO)
    log_options(options)
    try:
        run_init_checks(**options)
        connector_config = map_to_standard_config(options)
        processor_config = map_to_processor_config(options)
        sharepoint_fn(
            connector_config=connector_config,
            processor_config=processor_config,
            **options,
        )
    except Exception as e:
        logger.error(e, exc_info=True)
        raise click.ClickException(str(e)) from e


def get_cmd() -> click.Command:
    cmd = sharepoint
    add_recursive_option(cmd)
    add_shared_options(cmd)
    return cmd
