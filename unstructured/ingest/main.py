#!/usr/bin/env python3
import collections
import hashlib
import logging
import multiprocessing as mp
import sys
import warnings
from contextlib import suppress
from functools import partial
from pathlib import Path
from urllib.parse import urlparse

import click

from unstructured.ingest.connector.wikipedia import (
    SimpleWikipediaConfig,
    WikipediaConnector,
)
from unstructured.ingest.doc_processor.generalized import initialize, process_document
from unstructured.ingest.logger import ingest_log_streaming_init, logger

with suppress(RuntimeError):
    mp.set_start_method("spawn")


class MainProcess:
    def __init__(
        self,
        doc_connector,
        doc_processor_fn,
        num_processes,
        reprocess,
        verbose,
        max_docs,
    ):
        # initialize the reader and writer
        self.doc_connector = doc_connector
        self.doc_processor_fn = doc_processor_fn
        self.num_processes = num_processes
        self.reprocess = reprocess
        self.verbose = verbose
        self.max_docs = max_docs

    def initialize(self):
        """Slower initialization things: check connections, load things into memory, etc."""
        ingest_log_streaming_init(logging.DEBUG if self.verbose else logging.INFO)
        self.doc_connector.initialize()
        initialize()

    def cleanup(self):
        self.doc_connector.cleanup()

    def _filter_docs_with_outputs(self, docs):
        num_docs_all = len(docs)
        docs = [doc for doc in docs if not doc.has_output()]
        if self.max_docs is not None:
            if num_docs_all > self.max_docs:
                num_docs_all = self.max_docs
            docs = docs[: self.max_docs]
        num_docs_to_process = len(docs)
        if num_docs_to_process == 0:
            logger.info(
                "All docs have structured outputs, nothing to do. Use --reprocess to process all.",
            )
            return None
        elif num_docs_to_process != num_docs_all:
            logger.info(
                f"Skipping processing for {num_docs_all - num_docs_to_process} docs out of "
                f"{num_docs_all} since their structured outputs already exist, use --reprocess to "
                "reprocess those in addition to the unprocessed ones.",
            )
        return docs

    def run(self):
        self.initialize()

        # fetch the list of lazy downloading IngestDoc obj's
        docs = self.doc_connector.get_ingest_docs()

        # remove docs that have already been processed
        if not self.reprocess:
            docs = self._filter_docs_with_outputs(docs)
            if not docs:
                return

        # Debugging tip: use the below line and comment out the mp.Pool loop
        # block to remain in single process
        # self.doc_processor_fn(docs[0])

        with mp.Pool(
            processes=self.num_processes,
            initializer=ingest_log_streaming_init,
            initargs=(logging.DEBUG if self.verbose else logging.INFO,),
        ) as pool:
            pool.map(self.doc_processor_fn, docs)

        self.cleanup()


@click.command()  # type: ignore
@click.pass_context
@click.option(
    "--max-docs",
    default=None,
    type=int,
    help="If specified, process at most specified number of documents.",
)
@click.option(
    "--flatten-metadata",
    is_flag=True,
    default=False,
    help="Results in flattened json elements. "
    "Specifically, the metadata key values are brought to the top-level of the element, "
    "and the `metadata` key itself is removed.",
)
@click.option(
    "--fields-include",
    default="element_id,text,type,metadata",
    help="If set, include the specified top-level fields in an element. "
    "Default is `element_id,text,type,metadata`.",
)
@click.option(
    "--metadata-include",
    default=None,
    help="If set, include the specified metadata fields if they exist and drop all other fields. "
    "Usage: provide a single string with comma separated values. "
    "Example: --metadata-include filename,page_number ",
)
@click.option(
    "--metadata-exclude",
    default=None,
    help="If set, drop the specified metadata fields if they exist. "
    "Usage: provide a single string with comma separated values. "
    "Example: --metadata-exclude filename,page_number ",
)
@click.option(
    "--partition-by-api",
    is_flag=True,
    default=False,
    help="Use a remote API to partition the files."
    " Otherwise, use the function from partition.auto",
)
@click.option(
    "--partition-endpoint",
    default="https://api.unstructured.io/general/v0/general",
    help="If partitioning via api, use the following host. "
    "Default: https://api.unstructured.io/general/v0/general",
)
@click.option(
    "--partition-strategy",
    default="auto",
    help="The method that will be used to process the documents. "
    "Default: auto. Other strategies include `fast` and `hi_res`.",
)
@click.option(
    "--partition-ocr-languages",
    default="eng",
    help="A list of language packs to specify which languages to use for OCR, separated by '+' "
    "e.g. 'eng+deu' to use the English and German language packs. The appropriate Tesseract "
    "language pack needs to be installed."
    "Default: eng",
)
@click.option(
    "--encoding",
    default="utf-8",
    help="Text encoding to use when reading documents. Default: utf-8",
)
@click.option(
    "--api-key",
    default="",
    help="API Key for partition endpoint.",
)
@click.option(
    "--local-input-path",
    default=None,
    help="Path to the location in the local file system that will be processed.",
)
@click.option(
    "--local-file-glob",
    default=None,
    help="A comma-separated list of file globs to limit which types of local files are accepted,"
    " e.g. '*.html,*.txt'",
)
@click.option(
    "--remote-url",
    default=None,
    help="Remote fsspec URL formatted as `protocol://dir/path`, it can contain both "
    "a directory or a single file. Supported protocols are: `gcs`, `gs`, `s3`, `s3a`, `abfs` "
    "`az` and `dropbox`.",
)
@click.option(
    "--gcs-token",
    default=None,
    help="Token used to access Google Cloud. GCSFS will attempt to use your default gcloud creds"
    "or get creds from the google metadata service or fall back to anonymous access.",
)
@click.option(
    "--s3-anonymous",
    is_flag=True,
    default=False,
    help="Connect to s3 without local AWS credentials.",
)
@click.option(
    "--dropbox-token",
    default=None,
    help="Dropbox access token.",
)
@click.option(
    "--azure-account-name",
    default=None,
    help="Azure Blob Storage or DataLake account name.",
)
@click.option(
    "--azure-account-key",
    default=None,
    help="Azure Blob Storage or DataLake account key (not required if "
    "`azure_account_name` is public).",
)
@click.option(
    "--azure-connection-string",
    default=None,
    help="Azure Blob Storage or DataLake connection string.",
)
@click.option(
    "--drive-id",
    default=None,
    help="Google Drive File or Folder ID.",
)
@click.option(
    "--drive-service-account-key",
    default=None,
    help="Path to the Google Drive service account json file.",
)
@click.option(
    "--drive-extension",
    default=None,
    help="Filters the files to be processed based on extension e.g. .jpg, .docx, etc.",
)
@click.option(
    "--biomed-path",
    default=None,
    help="PMC Open Access FTP Directory Path.",
)
@click.option(
    "--biomed-api-id",
    default=None,
    help="ID parameter for OA Web Service API.",
)
@click.option(
    "--biomed-api-from",
    default=None,
    help="From parameter for OA Web Service API.",
)
@click.option(
    "--biomed-api-until",
    default=None,
    help="Until parameter for OA Web Service API.",
)
@click.option(
    "--biomed-max-retries",
    default=1,
    help="Max requests to OA Web Service API.",
)
@click.option(
    "--biomed-max-request-time",
    default=45,
    help="(In seconds) Max request time to OA Web Service API.",
)
@click.option(
    "--biomed-decay",
    default=0.3,
    help="(In float) Factor to multiply the delay between retries.",
)
@click.option(
    "--wikipedia-page-title",
    default=None,
    help='Title of a Wikipedia page, e.g. "Open source software".',
)
@click.option(
    "--wikipedia-auto-suggest",
    default=True,
    help="Whether to automatically suggest a page if the exact page was not found."
    " Set to False if the wrong Wikipedia page is fetched.",
)
@click.option(
    "--github-url",
    default=None,
    help='URL to GitHub repository, e.g. "https://github.com/Unstructured-IO/unstructured",'
    ' or a repository owner/name pair, e.g. "Unstructured-IO/unstructured"',
)
@click.option(
    "--gitlab-url",
    default=None,
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
@click.option(
    "--subreddit-name",
    default=None,
    help='The name of a subreddit, without the "r\\", e.g. "machinelearning"',
)
@click.option(
    "--reddit-client-id",
    default=None,
    help="The client ID, see "
    "https://praw.readthedocs.io/en/stable/getting_started/quick_start.html#prerequisites"
    " for more information.",
)
@click.option(
    "--reddit-client-secret",
    default=None,
    help="The client secret, see "
    "https://praw.readthedocs.io/en/stable/getting_started/quick_start.html#prerequisites"
    " for more information.",
)
@click.option(
    "--reddit-user-agent",
    default="Unstructured Ingest Subreddit fetcher",
    help="The user agent to use on the Reddit API, see "
    "https://praw.readthedocs.io/en/stable/getting_started/quick_start.html#prerequisites"
    " for more information.",
)
@click.option(
    "--reddit-search-query",
    default=None,
    help="If set, return posts using this query. Otherwise, use hot posts.",
)
@click.option("--reddit-num-posts", default=10, help="The number of posts to fetch.")
@click.option(
    "--re-download/--no-re-download",
    default=False,
    help="Re-download files even if they are already present in --download-dir.",
)
@click.option(
    "--download-only",
    is_flag=True,
    default=False,
    help="Download any files that are not already present in either --download-dir or "
    "the default download ~/.cache/... location in case --download-dir is not specified and "
    "skip processing them through unstructured.",
)
@click.option(
    "--slack-channels",
    default=None,
    help="Comma separated list of Slack channel IDs to pull messages from, "
    "can be a public or private channel",
)
@click.option(
    "--slack-token",
    default=None,
    help="Bot token used to access Slack API, must have channels:history " "scope for the bot user",
)
@click.option(
    "--start-date",
    default=None,
    help="Start date/time in formats YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS or "
    "YYYY-MM-DD+HH:MM:SS or YYYY-MM-DDTHH:MM:SStz",
)
@click.option(
    "--end-date",
    default=None,
    help="End date/time in formats YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS or "
    "YYYY-MM-DD+HH:MM:SS or YYYY-MM-DDTHH:MM:SStz",
)
@click.option(
    "--discord-channels",
    default=None,
    help="A comma separated list of discord channel ids to ingest from.",
)
@click.option(
    "--discord-token",
    default=None,
    help="Bot token used to access Discord API, must have "
    "READ_MESSAGE_HISTORY scope for the bot user",
)
@click.option(
    "--discord-period",
    default=None,
    help="Number of days to go back in the history of discord channels, must be an number",
)
@click.option(
    "--ms-client-id",
    default=None,
    help="Microsoft app client ID",
)
@click.option(
    "--ms-client-cred",
    default=None,
    help="Microsoft App client secret",
)
@click.option(
    "--ms-authority-url",
    default="https://login.microsoftonline.com",
    help="Authentication token provider for Microsoft apps, default is "
    "https://login.microsoftonline.com",
)
@click.option(
    "--ms-tenant",
    default="common",
    help="ID or domain name associated with your Azure AD instance",
)
@click.option(
    "--ms-user-pname",
    default=None,
    help="User principal name, usually is your Azure AD email.",
)
@click.option(
    "--ms-onedrive-folder",
    default=None,
    help="Folder to start parsing files from.",
)
@click.option(
    "--ms-user-email",
    default=None,
    help="Outlook email to download messages from.",
)
@click.option(
    "--ms-outlook-folders",
    default=None,
    help="Comma separated list of folders to download email messages from. "
    "Do not specify subfolders. Use quotes if spaces in folder names.",
)
@click.option(
    "--elasticsearch-url",
    default=None,
    help='URL to the Elasticsearch cluster, e.g. "http://localhost:9200"',
)
@click.option(
    "--elasticsearch-index-name",
    default=None,
    help="Name for the Elasticsearch index to pull data from",
)
@click.option(
    "--jq-query",
    default=None,
    help="JQ query to get and concatenate a subset of the fields from a JSON document. "
    "For a group of JSON documents, it assumes that all of the documents have the same schema. "
    "Currently only supported for the Elasticsearch connector. "
    "Example: --jq-query '{meta, body}'",
)
@click.option(
    "--confluence-url",
    default=None,
    help='URL to Confluence Cloud, e.g. "unstructured-ingest-test.atlassian.net"',
)
@click.option(
    "--confluence-user-email",
    default=None,
    help="Email to authenticate into Confluence Cloud",
)
@click.option(
    "--confluence-api-token",
    default=None,
    help="API Token to authenticate into Confluence Cloud. \
        Check https://developer.atlassian.com/cloud/confluence/basic-auth-for-rest-apis/ \
        for more info.",
)
@click.option(
    "--confluence-list-of-spaces",
    default=None,
    help="A list of confluence space ids to be fetched. From each fetched space, \
        --confluence-num-of-docs-from-each-space number of docs will be ingested. \
        --confluence-list-of-spaces and --confluence-num-of-spaces cannot be used at the same time",
)
@click.option(
    "--confluence-max-num-of-spaces",
    default=500,
    help="Number of confluence space ids to be fetched. From each fetched space, \
        --confluence-num-of-docs-from-each-space number of docs will be ingested. \
        --confluence-list-of-spaces and --confluence-num-of-spaces cannot be used at the same time",
)
@click.option(
    "--confluence-max-num-of-docs-from-each-space",
    default=100,
    help="Number of documents to be aimed to be ingested from each fetched confluence space. \
        If any space has fewer documents, all the documents from that space will be ingested. \
        Documents are not necessarily ingested in order of creation date.",
)
@click.option(
    "--download-dir",
    help="Where files are downloaded to, defaults to `$HOME/.cache/unstructured/ingest/<SHA256>`.",
)
@click.option(
    "--preserve-downloads",
    is_flag=True,
    default=False,
    help="Preserve downloaded files. Otherwise each file is removed after being processed "
    "successfully.",
)
@click.option(
    "--structured-output-dir",
    default="structured-output",
    help="Where to place structured output .json files.",
)
@click.option(
    "--reprocess",
    is_flag=True,
    default=False,
    help="Reprocess a downloaded file even if the relevant structured output .json file "
    "in --structured-output-dir already exists.",
)
@click.option(
    "--num-processes",
    default=2,
    show_default=True,
    help="Number of parallel processes to process docs in.",
)
@click.option(
    "--recursive",
    is_flag=True,
    default=False,
    help="Recursively download files in their respective folders"
    "otherwise stop at the files in provided folder level."
    " Supported protocols are: `gcs`, `gs`, `s3`, `s3a`, `abfs` "
    "`az`, `google drive`, `dropbox` and `local`.",
)
@click.option("-v", "--verbose", is_flag=True, default=False)
def main(
    ctx,
    remote_url,
    s3_anonymous,
    dropbox_token,
    gcs_token,
    azure_account_name,
    azure_account_key,
    azure_connection_string,
    drive_id,
    drive_service_account_key,
    drive_extension,
    biomed_path,
    biomed_api_id,
    biomed_api_from,
    biomed_api_until,
    biomed_max_retries,
    biomed_max_request_time,
    biomed_decay,
    wikipedia_page_title,
    wikipedia_auto_suggest,
    github_url,
    gitlab_url,
    git_access_token,
    git_branch,
    git_file_glob,
    subreddit_name,
    reddit_client_id,
    reddit_client_secret,
    reddit_user_agent,
    reddit_search_query,
    reddit_num_posts,
    re_download,
    slack_channels,
    slack_token,
    start_date,
    end_date,
    discord_channels,
    discord_token,
    discord_period,
    ms_client_id,
    ms_client_cred,
    ms_authority_url,
    ms_tenant,
    ms_user_pname,
    ms_onedrive_folder,
    ms_user_email,
    ms_outlook_folders,
    elasticsearch_url,
    elasticsearch_index_name,
    jq_query,
    confluence_url,
    confluence_user_email,
    confluence_api_token,
    confluence_list_of_spaces,
    confluence_max_num_of_spaces,
    confluence_max_num_of_docs_from_each_space,
    download_dir,
    preserve_downloads,
    structured_output_dir,
    reprocess,
    num_processes,
    recursive,
    verbose,
    metadata_include,
    metadata_exclude,
    fields_include,
    flatten_metadata,
    max_docs,
    partition_by_api,
    partition_endpoint,
    partition_strategy,
    partition_ocr_languages,
    encoding,
    api_key,
    local_input_path,
    local_file_glob,
    download_only,
):
    default_values = collections.Counter([option.default for option in ctx.command.params])
    passed_values = collections.Counter(ctx.params.values())
    if default_values == passed_values:
        return click.echo(ctx.get_help())
    if flatten_metadata and "metadata" not in fields_include:
        logger.warning(
            "`--flatten-metadata` is specified, but there is no metadata to flatten, "
            "since `metadata` is not specified in `--fields-include`.",
        )
    if "metadata" not in fields_include and (metadata_include or metadata_exclude):
        logger.warning(
            "Either `--metadata-include` or `--metadata-exclude` is specified"
            " while metadata is not specified in --fields-include.",
        )
    if metadata_exclude is not None and metadata_include is not None:
        logger.error(
            "Arguments `--metadata-include` and `--metadata-exclude` are "
            "mutually exclusive with each other.",
        )
        sys.exit(1)
    if (
        not partition_by_api
        and partition_endpoint != "https://api.unstructured.io/general/v0/general"
    ):
        logger.warning(
            "Ignoring --partition-endpoint because --partition-by-api was not set",
        )
    if (not preserve_downloads and not download_only) and download_dir:
        logger.warning(
            "Not preserving downloaded files but --download_dir is specified",
        )
    if local_input_path is not None and download_dir:
        logger.warning(
            "Files should already be in local file system: there is nothing to download, "
            "but --download-dir is specified.",
        )
        sys.exit(1)
    from unstructured.ingest.interfaces import StandardConnectorConfig

    if local_input_path is None and not download_dir:
        cache_path = Path.home() / ".cache" / "unstructured" / "ingest"
        if not cache_path.exists():
            cache_path.mkdir(parents=True, exist_ok=True)
        if remote_url:
            hashed_dir_name = hashlib.sha256(remote_url.encode("utf-8"))
        elif github_url:
            hashed_dir_name = hashlib.sha256(
                f"{github_url}_{git_branch}".encode("utf-8"),
            )
        elif gitlab_url:
            hashed_dir_name = hashlib.sha256(
                f"{gitlab_url}_{git_branch}".encode("utf-8"),
            )
        elif subreddit_name:
            hashed_dir_name = hashlib.sha256(
                subreddit_name.encode("utf-8"),
            )
        elif wikipedia_page_title:
            hashed_dir_name = hashlib.sha256(
                wikipedia_page_title.encode("utf-8"),
            )
        elif drive_id:
            hashed_dir_name = hashlib.sha256(
                drive_id.encode("utf-8"),
            )
        elif biomed_path or biomed_api_id or biomed_api_from or biomed_api_until:
            base_path = biomed_path
            if not biomed_path:
                base_path = (
                    f"{biomed_api_id or ''}-{biomed_api_from or ''}-" f"{biomed_api_until or ''}"
                )
            hashed_dir_name = hashlib.sha256(
                base_path.encode("utf-8"),
            )
        elif elasticsearch_url:
            hashed_dir_name = hashlib.sha256(
                f"{elasticsearch_url}_{elasticsearch_index_name}".encode("utf-8"),
            )
        elif ms_user_pname:
            hashed_dir_name = hashlib.sha256(
                f"{ms_tenant}_{ms_user_pname}".encode("utf-8"),
            )
        elif ms_user_email:
            hashed_dir_name = hashlib.sha256(ms_user_email.encode("utf-8"))
        elif confluence_url:
            hashed_dir_name = hashlib.sha256(
                f"{confluence_url}".encode("utf-8"),
            )
        else:
            raise ValueError(
                "This connector does not support saving downloads to ~/.cache/  ,"
                " --download-dir must be provided",
            )
        download_dir = cache_path / hashed_dir_name.hexdigest()[:10]
        if preserve_downloads:
            logger.warning(
                f"Preserving downloaded files but --download-dir is not specified,"
                f" using {download_dir}",
            )
    standard_config = StandardConnectorConfig(
        download_dir=download_dir,
        output_dir=structured_output_dir,
        download_only=download_only,
        fields_include=fields_include,
        flatten_metadata=flatten_metadata,
        metadata_exclude=metadata_exclude,
        metadata_include=metadata_include,
        partition_by_api=partition_by_api,
        partition_endpoint=partition_endpoint,
        preserve_downloads=preserve_downloads,
        re_download=re_download,
        api_key=api_key,
    )
    if remote_url:
        protocol = urlparse(remote_url).scheme
        if protocol in ("s3", "s3a"):
            from unstructured.ingest.connector.s3 import S3Connector, SimpleS3Config

            doc_connector = S3Connector(  # type: ignore
                standard_config=standard_config,
                config=SimpleS3Config(
                    path=remote_url,
                    recursive=recursive,
                    access_kwargs={"anon": s3_anonymous},
                ),
            )
        elif protocol in ("gs", "gcs"):
            from unstructured.ingest.connector.gcs import GcsConnector, SimpleGcsConfig

            doc_connector = GcsConnector(  # type: ignore
                standard_config=standard_config,
                config=SimpleGcsConfig(
                    path=remote_url,
                    recursive=recursive,
                    access_kwargs={"token": gcs_token},
                ),
            )
        elif protocol in ("dropbox"):
            from unstructured.ingest.connector.dropbox import (
                DropboxConnector,
                SimpleDropboxConfig,
            )

            doc_connector = DropboxConnector(  # type: ignore
                standard_config=standard_config,
                config=SimpleDropboxConfig(
                    path=remote_url,
                    recursive=recursive,
                    access_kwargs={"token": dropbox_token},
                ),
            )
        elif protocol in ("abfs", "az"):
            from unstructured.ingest.connector.azure import (
                AzureBlobStorageConnector,
                SimpleAzureBlobStorageConfig,
            )

            if azure_account_name:
                access_kwargs = {
                    "account_name": azure_account_name,
                    "account_key": azure_account_key,
                }
            elif azure_connection_string:
                access_kwargs = {"connection_string": azure_connection_string}
            else:
                access_kwargs = {}
            doc_connector = AzureBlobStorageConnector(  # type: ignore
                standard_config=standard_config,
                config=SimpleAzureBlobStorageConfig(
                    path=remote_url,
                    recursive=recursive,
                    access_kwargs=access_kwargs,
                ),
            )
        else:
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
                standard_config=standard_config,
                config=SimpleFsspecConfig(
                    path=remote_url,
                    recursive=recursive,
                ),
            )
    elif github_url:
        from unstructured.ingest.connector.github import (
            GitHubConnector,
            SimpleGitHubConfig,
        )

        doc_connector = GitHubConnector(  # type: ignore
            standard_config=standard_config,
            config=SimpleGitHubConfig(
                url=github_url,
                access_token=git_access_token,
                branch=git_branch,
                file_glob=git_file_glob,
            ),
        )
    elif gitlab_url:
        from unstructured.ingest.connector.gitlab import (
            GitLabConnector,
            SimpleGitLabConfig,
        )

        doc_connector = GitLabConnector(  # type: ignore
            standard_config=standard_config,
            config=SimpleGitLabConfig(
                url=gitlab_url,
                access_token=git_access_token,
                branch=git_branch,
                file_glob=git_file_glob,
            ),
        )
    elif subreddit_name:
        from unstructured.ingest.connector.reddit import (
            RedditConnector,
            SimpleRedditConfig,
        )

        doc_connector = RedditConnector(  # type: ignore
            standard_config=standard_config,
            config=SimpleRedditConfig(
                subreddit_name=subreddit_name,
                client_id=reddit_client_id,
                client_secret=reddit_client_secret,
                user_agent=reddit_user_agent,
                search_query=reddit_search_query,
                num_posts=reddit_num_posts,
            ),
        )
    elif slack_channels:
        from unstructured.ingest.connector.slack import (
            SimpleSlackConfig,
            SlackConnector,
        )

        doc_connector = SlackConnector(  # type: ignore
            standard_config=standard_config,
            config=SimpleSlackConfig(
                channels=SimpleSlackConfig.parse_channels(slack_channels),
                token=slack_token,
                oldest=start_date,
                latest=end_date,
                verbose=verbose,
            ),
        )
    elif discord_channels:
        from unstructured.ingest.connector.discord import (
            DiscordConnector,
            SimpleDiscordConfig,
        )

        doc_connector = DiscordConnector(  # type: ignore
            standard_config=standard_config,
            config=SimpleDiscordConfig(
                channels=SimpleDiscordConfig.parse_channels(discord_channels),
                days=discord_period,
                token=discord_token,
                verbose=verbose,
            ),
        )
    elif wikipedia_page_title:
        doc_connector = WikipediaConnector(  # type: ignore
            standard_config=standard_config,
            config=SimpleWikipediaConfig(
                title=wikipedia_page_title,
                auto_suggest=wikipedia_auto_suggest,
            ),
        )
    elif drive_id:
        from unstructured.ingest.connector.google_drive import (
            GoogleDriveConnector,
            SimpleGoogleDriveConfig,
        )

        doc_connector = GoogleDriveConnector(  # type: ignore
            standard_config=standard_config,
            config=SimpleGoogleDriveConfig(
                drive_id=drive_id,
                service_account_key=drive_service_account_key,
                recursive=recursive,
                extension=drive_extension,
            ),
        )
    elif biomed_path or biomed_api_id or biomed_api_from or biomed_api_until:
        from unstructured.ingest.connector.biomed import (
            BiomedConnector,
            SimpleBiomedConfig,
        )

        doc_connector = BiomedConnector(  # type: ignore
            standard_config=standard_config,
            config=SimpleBiomedConfig(
                path=biomed_path,
                id_=biomed_api_id,
                from_=biomed_api_from,
                until=biomed_api_until,
                max_retries=biomed_max_retries,
                request_timeout=biomed_max_request_time,
                decay=biomed_decay,
            ),
        )
    elif ms_client_id and ms_user_pname:
        from unstructured.ingest.connector.onedrive import (
            OneDriveConnector,
            SimpleOneDriveConfig,
        )

        doc_connector = OneDriveConnector(  # type: ignore
            standard_config=standard_config,
            config=SimpleOneDriveConfig(
                client_id=ms_client_id,
                client_credential=ms_client_cred,
                user_pname=ms_user_pname,
                tenant=ms_tenant,
                authority_url=ms_authority_url,
                folder=ms_onedrive_folder,
                recursive=recursive,
            ),
        )

    elif ms_client_id and ms_user_email:
        from unstructured.ingest.connector.outlook import (
            OutlookConnector,
            SimpleOutlookConfig,
        )

        doc_connector = OutlookConnector(  # type: ignore
            standard_config=standard_config,
            config=SimpleOutlookConfig(
                client_id=ms_client_id,
                client_credential=ms_client_cred,
                user_email=ms_user_email,
                tenant=ms_tenant,
                authority_url=ms_authority_url,
                ms_outlook_folders=SimpleOutlookConfig.parse_folders(ms_outlook_folders),
                recursive=recursive,
            ),
        )

    elif local_input_path:
        from unstructured.ingest.connector.local import (
            LocalConnector,
            SimpleLocalConfig,
        )

        doc_connector = LocalConnector(  # type: ignore
            standard_config=standard_config,
            config=SimpleLocalConfig(
                input_path=local_input_path,
                recursive=recursive,
                file_glob=local_file_glob,
            ),
        )
    elif elasticsearch_url:
        from unstructured.ingest.connector.elasticsearch import (
            ElasticsearchConnector,
            SimpleElasticsearchConfig,
        )

        doc_connector = ElasticsearchConnector(  # type: ignore
            standard_config=standard_config,
            config=SimpleElasticsearchConfig(
                url=elasticsearch_url,
                index_name=elasticsearch_index_name,
                jq_query=jq_query,
            ),
        )
    elif confluence_url:
        from unstructured.ingest.connector.confluence import (
            ConfluenceConnector,
            SimpleConfluenceConfig,
        )

        doc_connector = ConfluenceConnector(  # type: ignore
            standard_config=standard_config,
            config=SimpleConfluenceConfig(
                url=confluence_url,
                user_email=confluence_user_email,
                api_token=confluence_api_token,
                list_of_spaces=confluence_list_of_spaces,
                max_number_of_spaces=confluence_max_num_of_spaces,
                max_number_of_docs_from_each_space=confluence_max_num_of_docs_from_each_space,
            ),
        )
    # Check for other connector-specific options here and define the doc_connector object
    # e.g. "elif azure_container:  ..."

    else:
        logger.error("No connector-specific option was specified!")
        sys.exit(1)

    process_document_with_partition_args = partial(
        process_document,
        strategy=partition_strategy,
        ocr_languages=partition_ocr_languages,
        encoding=encoding,
    )

    MainProcess(
        doc_connector=doc_connector,
        doc_processor_fn=process_document_with_partition_args,
        num_processes=num_processes,
        reprocess=reprocess,
        verbose=verbose,
        max_docs=max_docs,
    ).run()


if __name__ == "__main__":
    main()  # type: ignore
