import typing as t

import click

from .airtable import get_source_cmd as airtable_src
from .azure import get_source_cmd as azure_src
from .azure_cognitive_search import get_dest_cmd as azure_cognitive_search_dest
from .biomed import get_source_cmd as biomed_src
from .box import get_source_cmd as box_src
from .confluence import get_source_cmd as confluence_src
from .delta_table import get_dest_cmd as delta_table_dest
from .delta_table import get_source_cmd as delta_table_src
from .discord import get_source_cmd as discord_src
from .dropbox import get_source_cmd as dropbox_src
from .elasticsearch import get_source_cmd as elasticsearch_src
from .fsspec import get_source_cmd as fsspec_src
from .gcs import get_source_cmd as gcs_src
from .github import get_source_cmd as github_src
from .gitlab import get_source_cmd as gitlab_src
from .google_drive import get_source_cmd as google_drive_src
from .jira import get_source_cmd as jira_src
from .local import get_source_cmd as local_src
from .notion import get_source_cmd as notion_src
from .onedrive import get_source_cmd as onedrive_src
from .outlook import get_source_cmd as outlook_src
from .reddit import get_source_cmd as reddit_src
from .s3 import get_dest_cmd as s3_dest
from .s3 import get_source_cmd as s3_src
from .salesforce import get_source_cmd as salesforce_src
from .sharepoint import get_source_cmd as sharepoint_src
from .slack import get_source_cmd as slack_src
from .wikipedia import get_source_cmd as wikipedia_src

src: t.List[click.Group] = [
    airtable_src(),
    azure_src(),
    biomed_src(),
    box_src(),
    confluence_src(),
    delta_table_src(),
    discord_src(),
    dropbox_src(),
    elasticsearch_src(),
    fsspec_src(),
    gcs_src(),
    github_src(),
    gitlab_src(),
    google_drive_src(),
    jira_src(),
    local_src(),
    notion_src(),
    onedrive_src(),
    outlook_src(),
    reddit_src(),
    salesforce_src(),
    sharepoint_src(),
    slack_src(),
    s3_src(),
    wikipedia_src(),
]

dest: t.List[click.Command] = [azure_cognitive_search_dest(), s3_dest(), delta_table_dest()]

__all__ = [
    "src",
    "dest",
]
