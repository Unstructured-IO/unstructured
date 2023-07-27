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
    github_fn(**options)


def github_fn(**options):
    run_init_checks(options=options)
    ingest_log_streaming_init(logging.DEBUG if options["verbose"] else logging.INFO)
    log_options(options=options)

    hashed_dir_name = hashlib.sha256(
        "{url}_{git_branch}".format(url=options["url"], git_branch=options["git_branch"]).encode(
            "utf-8",
        ),
    )
    update_download_dir_hash(options=options, hashed_dir_name=hashed_dir_name, logger=logger)

    from unstructured.ingest.connector.github import (
        GitHubConnector,
        SimpleGitHubConfig,
    )

    doc_connector = GitHubConnector(  # type: ignore
        standard_config=map_to_standard_config(options=options),
        config=SimpleGitHubConfig(
            url=options["url"],
            access_token=options["git_access_token"],
            branch=options["git_branch"],
            file_glob=options["git_file_glob"],
        ),
    )

    process_documents(doc_connector=doc_connector, options=options)
