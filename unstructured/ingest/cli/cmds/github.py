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
from unstructured.ingest.runner import github as github_fn


@click.command()
@click.option(
    "--git-access-token",
    default=None,
    help="A GitHub or GitLab access token, see https://docs.github.com/en/authentication "
    " or https://docs.gitlab.com/ee/api/rest/index.html#personalprojectgroup-access-tokens",
)
@click.option(
    "--git-branch",
    default=None,
    help="The branch for which to fetch files from. If not given,"
    " the default repository branch is used.",
)
@click.option(
    "--git-file-glob",
    default=None,
    help="A comma-separated list of file globs to limit which types of files are accepted,"
    " e.g. '*.html,*.txt'",
)
@click.option(
    "--url",
    required=True,
    help='URL to GitHub repository, e.g. "https://github.com/Unstructured-IO/unstructured",'
    ' or a repository owner/name pair, e.g. "Unstructured-IO/unstructured"',
)
def github(**options):
    verbose = options.get("verbose", False)
    ingest_log_streaming_init(logging.DEBUG if verbose else logging.INFO)
    log_options(options)
    try:
        run_init_checks(**options)
        connector_config = map_to_standard_config(options)
        processor_config = map_to_processor_config(options)
        github_fn(connector_config=connector_config, processor_config=processor_config, **options)
    except Exception as e:
        logger.error(e, exc_info=True)
        raise click.ClickException(str(e)) from e


def get_cmd() -> click.Command:
    cmd = github
    add_shared_options(cmd)
    return cmd
