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
    "--jql-query",
    default=None,
    help="...",
)
@click.option(
    "--list-of-paths",
    default=None,
    help="""A list of paths that specify the locations to ingest data from within Jira.

    If this argument is not set, the connector ingests all issues within each and every project.
    --list-of-paths: path1 path2 path3 ….
    path: project_id/board_id(optional)/epic_id(optional)/issue_id(optional)

    To obtain project, board, epic, issue ids in bulk, check:
    ...

    To obtain specific ids from Jira UI, go to your Jira page, and ...:

    You can also check:
    https://confluence.atlassian.com/cloudkb/how-to-identify-the-jira-issue-id-in-cloud-1167747456.html

    Here is an example for one --list-of-paths:
        project1/		→ gets the all issues inside project1
        ...

    Examples to invalid airtable_paths:
        ...          → has to mention base to be valid
        .../...     → has to mention table to be valid
    """,
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
