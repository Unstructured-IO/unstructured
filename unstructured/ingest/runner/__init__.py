import typing as t

from .airtable import Airtable
from .azure import Azure
from .biomed import Biomed
from .box import Box
from .confluence import Confluence
from .delta_table import DeltaTable
from .discord import Discord
from .dropbox import Dropbox
from .elasticsearch import ElasticSearch
from .fsspec import Fsspec
from .gcs import GCS
from .github import Github
from .gitlab import Gitlab
from .google_drive import GoogleDrive
from .jira import Jira
from .local import Local
from .notion import Notion
from .onedrive import OneDrive
from .outlook import Outlook
from .reddit import Reddit
from .s3 import S3
from .salesforce import salesforce
from .sharepoint import SharePoint
from .slack import slack
from .wikipedia import wikipedia

runner_map: t.Dict[str, t.Callable] = {
    "airtable": Airtable,
    "azure": Azure,
    "biomed": Biomed,
    "box": Box,
    "confluence": Confluence,
    "delta_table": DeltaTable,
    "discord": Discord,
    "dropbox": Dropbox,
    "elasticsearch": ElasticSearch,
    "fsspec": Fsspec,
    "gcs": GCS,
    "github": Github,
    "gitlab": Gitlab,
    "gdrive": GoogleDrive,
    "google_drive": GoogleDrive,
    "jira": Jira,
    "local": Local,
    "notion": Notion,
    "onedrive": OneDrive,
    "outlook": Outlook,
    "reddit": Reddit,
    "s3": S3,
    "salesforce": salesforce,
    "sharepoint": SharePoint,
    "slack": slack,
    "wikipedia": wikipedia,
}

__all__ = [
    "Airtable",
    "Azure",
    "Biomed",
    "Box",
    "Confluence",
    "DeltaTable",
    "Discord",
    "Dropbox",
    "ElasticSearch",
    "Fsspec",
    "GCS",
    "GoogleDrive",
    "Github",
    "Gitlab",
    "Jira",
    "Local",
    "Notion",
    "OneDrive",
    "Outlook",
    "Reddit",
    "S3",
    "salesforce",
    "SharePoint",
    "slack",
    "wikipedia",
    "runner_map",
]
