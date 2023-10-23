import typing as t
from typing import Type

from .airtable import AirtableRunner
from .azure import AzureRunner
from .base_runner import FsspecBaseRunner, Runner
from .biomed import BiomedRunner
from .box import BoxRunner
from .confluence import ConfluenceRunner
from .delta_table import DeltaTableRunner
from .discord import DiscordRunner
from .dropbox import DropboxRunner
from .elasticsearch import ElasticSearchRunner
from .fsspec import FsspecRunner
from .gcs import GCSRunner
from .github import GithubRunner
from .gitlab import GitlabRunner
from .google_drive import GoogleDriveRunner
from .jira import JiraRunner
from .local import LocalRunner
from .notion import NotionRunner
from .onedrive import OneDriveRunner
from .outlook import OutlookRunner
from .reddit import RedditRunner
from .s3 import S3Runner
from .salesforce import SalesforceRunner
from .sharepoint import SharePointRunner
from .slack import SlackRunner
from .wikipedia import WikipediaRunner

runner_map: t.Dict[str, Type[Runner]] = {
    "airtable": AirtableRunner,
    "azure": AzureRunner,
    "biomed": BiomedRunner,
    "box": BoxRunner,
    "confluence": ConfluenceRunner,
    "delta_table": DeltaTableRunner,
    "discord": DiscordRunner,
    "dropbox": DropboxRunner,
    "elasticsearch": ElasticSearchRunner,
    "fsspec": FsspecRunner,
    "gcs": GCSRunner,
    "github": GithubRunner,
    "gitlab": GitlabRunner,
    "gdrive": GoogleDriveRunner,
    "google_drive": GoogleDriveRunner,
    "jira": JiraRunner,
    "local": LocalRunner,
    "notion": NotionRunner,
    "onedrive": OneDriveRunner,
    "outlook": OutlookRunner,
    "reddit": RedditRunner,
    "s3": S3Runner,
    "salesforce": SalesforceRunner,
    "sharepoint": SharePointRunner,
    "slack": SlackRunner,
    "wikipedia": WikipediaRunner,
}

__all__ = [
    "AirtableRunner",
    "AzureRunner",
    "BiomedRunner",
    "BoxRunner",
    "ConfluenceRunner",
    "DeltaTableRunner",
    "DiscordRunner",
    "DropboxRunner",
    "ElasticSearchRunner",
    "FsspecRunner",
    "GCSRunner",
    "GoogleDriveRunner",
    "GithubRunner",
    "GitlabRunner",
    "JiraRunner",
    "LocalRunner",
    "NotionRunner",
    "OneDriveRunner",
    "OutlookRunner",
    "RedditRunner",
    "S3Runner",
    "SalesforceRunner",
    "SharePointRunner",
    "SlackRunner",
    "WikipediaRunner",
    "runner_map",
    "Runner",
    "FsspecBaseRunner",
]
