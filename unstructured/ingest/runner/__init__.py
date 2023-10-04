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
from .gitlab import gitlab
from .google_drive import gdrive
from .jira import jira
from .local import local
from .notion import notion
from .onedrive import onedrive
from .outlook import outlook
from .reddit import reddit
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
    "gitlab": gitlab,
    "gdrive": gdrive,
    "google_drive": gdrive,
    "jira": jira,
    "local": local,
    "notion": notion,
    "onedrive": onedrive,
    "outlook": outlook,
    "reddit": reddit,
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
    "gdrive",
    "Github",
    "gitlab",
    "jira",
    "local",
    "notion",
    "onedrive",
    "outlook",
    "reddit",
    "S3",
    "salesforce",
    "SharePoint",
    "slack",
    "wikipedia",
    "runner_map",
]
