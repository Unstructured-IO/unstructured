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
    help='URL to GitLab repository, e.g. "https://gitlab.com/gitlab-com/content-sites/docsy-gitlab"'
    ', or a repository path, e.g. "gitlab-com/content-sites/docsy-gitlab"',
)
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
def gitlab(ctx, url, git_access_token, git_branch, git_file_glob):
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
    hashed_dir_name = hashlib.sha256(
        f"{url}_{git_branch}".encode("utf-8"),
    )
    update_download_dir_hash(ctx_dict=context_dict, hashed_dir_name=hashed_dir_name, logger=logger)

    from unstructured.ingest.connector.gitlab import (
        GitLabConnector,
        SimpleGitLabConfig,
    )

    doc_connector = GitLabConnector(  # type: ignore
        standard_config=map_to_standard_config(context_dict),
        config=SimpleGitLabConfig(
            url=url,
            access_token=git_access_token,
            branch=git_branch,
            file_glob=git_file_glob,
        ),
    )

    process_documents(doc_connector=doc_connector, ctx_dict=context_dict)
