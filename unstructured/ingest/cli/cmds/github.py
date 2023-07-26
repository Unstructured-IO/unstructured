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
    "--url",
    required=True,
    help='URL to GitHub repository, e.g. "https://github.com/Unstructured-IO/unstructured",'
    ' or a repository owner/name pair, e.g. "Unstructured-IO/unstructured"',
)
@click.option(
    "--git-access-token",
    required=True,
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
def github(ctx, url, git_access_token, git_branch, git_file_glob):
    context_dict = ctx.obj
    ingest_log_streaming_init(logging.DEBUG if context_dict["verbose"] else logging.INFO)

    logger.debug(f"parent params: {context_dict}")
    logger.debug(
        "params: {}".format(
            {
                "url": url,
                "git_access_token": git_access_token,
                "git_branch": git_branch,
                "git_file_glob": git_file_glob,
            },
        ),
    )
    hashed_dir_name = str(
        hashlib.sha256(
            f"{url}_{git_branch}".encode("utf-8"),
        ),
    )
    update_download_dir_hash(ctx_dict=context_dict, hashed_dir_name=hashed_dir_name, logger=logger)

    from unstructured.ingest.connector.github import (
        GitHubConnector,
        SimpleGitHubConfig,
    )

    doc_connector = GitHubConnector(  # type: ignore
        standard_config=map_to_standard_config(context_dict),
        config=SimpleGitHubConfig(
            url=url,
            access_token=git_access_token,
            branch=git_branch,
            file_glob=git_file_glob,
        ),
    )

    process_documents(doc_connector=doc_connector, ctx_dict=context_dict)
