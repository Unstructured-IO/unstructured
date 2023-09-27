import typing as t

from .airtable import airtable
from .azure import azure
from .biomed import biomed
from .box import box
from .confluence import confluence
from .delta_table import delta_table
from .discord import discord
from .dropbox import dropbox
from .elasticsearch import elasticsearch
from .fsspec import fsspec
from .gcs import gcs
from .github import github
from .gitlab import gitlab
from .google_drive import gdrive
from .jira import jira
from .local import local
from .notion import notion
from .onedrive import onedrive
from .outlook import outlook
from .reddit import reddit
from .s3 import s3
from .salesforce import salesforce
from .sharepoint import SharePoint
from .slack import slack
from .wikipedia import wikipedia

runner_map: t.Dict[str, t.Callable] = {
    "airtable": airtable,
    "azure": azure,
    "biomed": biomed,
    "box": box,
    "confluence": confluence,
    "delta_table": delta_table,
    "discord": discord,
    "dropbox": dropbox,
    "elasticsearch": elasticsearch,
    "fsspec": fsspec,
    "gcs": gcs,
    "github": github,
    "gitlab": gitlab,
    "gdrive": gdrive,
    "google_drive": gdrive,
    "jira": jira,
    "local": local,
    "notion": notion,
    "onedrive": onedrive,
    "outlook": outlook,
    "reddit": reddit,
    "s3": s3,
    "salesforce": salesforce,
    "sharepoint": SharePoint,
    "slack": slack,
    "wikipedia": wikipedia,
}

__all__ = [
    "airtable",
    "azure",
    "biomed",
    "box",
    "confluence",
    "delta_table",
    "discord",
    "dropbox",
    "elasticsearch",
    "fsspec",
    "gcs",
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
    "SharePoint",
    "slack",
    "wikipedia",
    "runner_map",
]
