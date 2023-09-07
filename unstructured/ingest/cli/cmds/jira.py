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
from unstructured.ingest.runner import jira as jira_fn


@click.command()
@click.option(
    "--api-token",
    required=True,
    help="API Token to authenticate into Jira (into Atlassian). \
        Check https://developer.atlassian.com/cloud/jira/platform/basic-auth-for-rest-apis/ \
        for more info.",
)
@click.option(
    "--list-of-projects",
    default=None,
    help="Space separated project ids or keys. Use Jira UI or the API to find or obtain keys.\
        Alternatively, use API to obtain ids.",
)
@click.option(
    "--list-of-boards",
    default=None,
    help="Space separated board ids. Check board URL, or use the API to find the board ids.",
)
@click.option(
    "--list-of-issues",
    default=None,
    help="Space separated issue ids or keys. Use Jira UI or the API to find or obtain keys.\
        Alternatively, use API to obtain ids.",
)
@click.option(
    "--url",
    required=True,
    help='URL to Atlassian (Jira) Cloud, e.g. "unstructured-jira-connector-test.atlassian.net"',
)
@click.option(
    "--user-email",
    required=True,
    help="Email to authenticate into Atlassian (Jira) Cloud.",
)
def jira(
    **options,
):
    verbose = options.get("verbose", False)
    ingest_log_streaming_init(logging.DEBUG if verbose else logging.INFO)
    log_options(options)
    try:
        run_init_checks(**options)
        connector_config = map_to_standard_config(options)
        processor_config = map_to_processor_config(options)
        jira_fn(
            connector_config=connector_config,
            processor_config=processor_config,
            **options,
        )
    except Exception as e:
        logger.error(e, exc_info=True)
        raise click.ClickException(str(e)) from e


def get_cmd() -> click.Command:
    cmd = jira
    add_shared_options(cmd)
    return cmd
