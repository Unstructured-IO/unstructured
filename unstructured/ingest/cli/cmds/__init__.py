import typing as t

import click

from .airtable import get_source_cmd as airtable_src
from .azure import get_source_cmd as azure_src
from .biomed import get_source_cmd as biomed_src
from .box import get_source_cmd as box_src
from .confluence import get_source_cmd as confluence_src
from .delta_table import get_source_cmd as delta_table_src
from .discord import get_source_cmd as discord_src
from .dropbox import get_source_cmd as dropbox_src
from .elasticsearch import get_source_cmd as elasticsearch_src
from .fsspec import get_source_cmd as fsspec_src
from .gcs import get_source_cmd as gcs_src
from .github import get_source_cmd as github_src
from .gitlab import get_source_cmd as gitlab_src
<<<<<<< HEAD
from .google_drive import get_cmd as gdrive
from .jira import get_cmd as jira
=======
from .google_drive import get_source_cmd as google_drive_src
>>>>>>> cb5b5734 (refactor google drive connectors)
from .local import get_cmd as local
from .notion import get_cmd as notion
from .onedrive import get_cmd as onedrive
from .outlook import get_cmd as outlook
from .reddit import get_cmd as reddit
from .s3 import get_dest_cmd as s3_dest
from .s3 import get_source_cmd as s3_src
from .salesforce import get_cmd as salesforce
from .sharepoint import get_cmd as sharepoint
from .slack import get_cmd as slack
from .wikipedia import get_cmd as wikipedia

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
    s3_src(),
]

dest: t.List[click.Command] = [s3_dest()]

__all__ = [
    "jira",
    "local",
    "notion",
    "onedrive",
    "outlook",
    "reddit",
    "s3",
    "salesforce",
    "sharepoint",
    "slack",
    "wikipedia",
    "src",
    "dest",
]
