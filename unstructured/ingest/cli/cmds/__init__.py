from .airtable import get_base_src_cmd as airtable_base_src_cmd
from .azure import get_base_src_cmd as azure_base_src_cmd
from .biomed import get_base_src_cmd as biomed_base_src_cmd
from .box import get_base_src_cmd as box_base_src_cmd
from .confluence import get_base_src_cmd as confluence_base_src_cmd
from .delta_table import get_base_src_cmd as delta_table_base_src_cmd
from .discord import get_base_src_cmd as discord_base_src_cmd
from .dropbox import get_base_src_cmd as dropbox_base_src_cmd
from .elasticsearch import get_base_src_cmd as elasticsearch_base_src_cmd
from .fsspec import get_base_src_cmd as fsspec_base_src_cmd
from .gcs import get_base_src_cmd as gcs_base_src_cmd
from .github import get_base_src_cmd as github_base_src_cmd
from .gitlab import get_base_src_cmd as gitlab_base_src_cmd
from .google_drive import get_base_src_cmd as google_drive_base_src_cmd
from .jira import get_base_src_cmd as jira_base_src_cmd
from .local import get_base_src_cmd as local_base_src_cmd
from .notion import get_base_src_cmd as notion_base_src_cmd
from .onedrive import get_base_src_cmd as onedrive_base_src_cmd
from .outlook import get_base_src_cmd as outlook_base_src_cmd
from .reddit import get_base_src_cmd as reddit_base_src_cmd
from .s3 import get_base_dest_cmd as s3_base_dest_cmd
from .s3 import get_base_src_cmd as s3_base_src_cmd
from .salesforce import get_base_src_cmd as salesforce_base_src_cmd
from .sharepoint import get_base_src_cmd as sharepoint_base_src_cmd
from .slack import get_base_src_cmd as slack_base_src_cmd
from .wikipedia import get_base_src_cmd as wikipedia_base_src_cmd

base_src_cmd_fns = [
    airtable_base_src_cmd,
    azure_base_src_cmd,
    biomed_base_src_cmd,
    box_base_src_cmd,
    confluence_base_src_cmd,
    delta_table_base_src_cmd,
    discord_base_src_cmd,
    dropbox_base_src_cmd,
    elasticsearch_base_src_cmd,
    fsspec_base_src_cmd,
    gcs_base_src_cmd,
    github_base_src_cmd,
    gitlab_base_src_cmd,
    google_drive_base_src_cmd,
    jira_base_src_cmd,
    local_base_src_cmd,
    notion_base_src_cmd,
    onedrive_base_src_cmd,
    outlook_base_src_cmd,
    reddit_base_src_cmd,
    salesforce_base_src_cmd,
    sharepoint_base_src_cmd,
    slack_base_src_cmd,
    s3_base_src_cmd,
    wikipedia_base_src_cmd,
]

base_dest_cmd_fns = [
    s3_base_dest_cmd,
]

__all__ = [
    "base_src_cmd_fns",
    "base_dest_cmd_fns",
]
