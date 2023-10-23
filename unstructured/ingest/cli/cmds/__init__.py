import collections
import typing as t

import click

from .airtable import get_base_cmd as airtable_base_cmd
from .azure import get_base_cmd as azure_base_cmd
from .biomed import get_base_cmd as biomed_base_cmd
from .box import get_base_cmd as box_base_cmd
from .confluence import get_base_cmd as confluence_base_cmd
from .delta_table import get_base_cmd as delta_table_base_cmd
from .discord import get_base_cmd as discord_base_cmd
from .dropbox import get_base_cmd as dropbox_base_cmd
from .elasticsearch import get_base_cmd as elasticsearch_base_cmd
from .fsspec import get_base_cmd as fsspec_base_cmd
from .gcs import get_base_cmd as gcs_base_cmd
from .github import get_base_cmd as github_base_cmd
from .gitlab import get_base_cmd as gitlab_base_cmd
from .google_drive import get_base_cmd as google_drive_base_cmd
from .jira import get_base_cmd as jira_base_cmd
from .local import get_base_cmd as local_base_cmd
from .notion import get_base_cmd as notion_base_cmd
from .onedrive import get_base_cmd as onedrive_base_cmd
from .outlook import get_base_cmd as outlook_base_cmd
from .reddit import get_base_cmd as reddit_base_cmd
from .s3 import get_base_cmd as s3_base_cmd
from .salesforce import get_base_cmd as salesforce_base_cmd
from .sharepoint import get_base_cmd as sharepoint_base_cmd
from .slack import get_base_cmd as slack_base_cmd
from .wikipedia import get_base_cmd as wikipedia_base_cmd

base_cmds = [
    airtable_base_cmd(),
    azure_base_cmd(),
    biomed_base_cmd(),
    box_base_cmd(),
    confluence_base_cmd(),
    delta_table_base_cmd(),
    discord_base_cmd(),
    dropbox_base_cmd(),
    elasticsearch_base_cmd(),
    fsspec_base_cmd(),
    gcs_base_cmd(),
    github_base_cmd(),
    gitlab_base_cmd(),
    google_drive_base_cmd(),
    jira_base_cmd(),
    local_base_cmd(),
    notion_base_cmd(),
    onedrive_base_cmd(),
    outlook_base_cmd(),
    reddit_base_cmd(),
    salesforce_base_cmd(),
    sharepoint_base_cmd(),
    slack_base_cmd(),
    s3_base_cmd(),
    wikipedia_base_cmd(),
]

# Make sure there are not overlapping names
cmd_names = [b.cmd_name for b in base_cmds]
duplicates = [item for item, count in collections.Counter(cmd_names).items() if count > 1]
if len(cmd_names) != len(list(set(cmd_names))):
    raise ValueError(
        "multiple base commands defined with the same names: {}".format(", ".join(duplicates)),
    )

src: t.List[click.Group] = [b.get_src_cmd() for b in base_cmds if b.get_src_cmd()]

dest: t.List[click.Command] = [b.get_dest_cmd() for b in base_cmds if b.get_dest_cmd()]

# dest: t.List[click.Command] = [azure_cognitive_search_dest(), s3_dest(), delta_table_dest()]

__all__ = [
    "src",
    "dest",
]
