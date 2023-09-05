import typing as t

import click

from .airtable import get_cmd as airtable
from .azure import get_source_cmd as azure_src
from .biomed import get_cmd as biomed
from .box import get_source_cmd as box_src
from .confluence import get_cmd as confluence
from .delta_table import get_cmd as delta_table
from .discord import get_cmd as discord
from .dropbox import get_source_cmd as dropbox_src
from .elasticsearch import get_cmd as elasticsearch
from .fsspec import get_source_cmd as fsspec_src
from .gcs import get_source_cmd as gcs_src
from .github import get_cmd as github
from .gitlab import get_cmd as gitlab
from .google_drive import get_cmd as gdrive
from .jira import get_cmd as jira
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
    s3_src(),
    azure_src(),
    box_src(),
    dropbox_src(),
    fsspec_src(),
    gcs_src(),
]

dest: t.List[click.Command] = [s3_dest()]

__all__ = [
    "airtable",
    "biomed",
    "confluence",
    "delta_table",
    "discord",
    "elasticsearch",
    "gdrive",
    "github",
    "gitlab",
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
