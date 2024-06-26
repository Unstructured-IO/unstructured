import typing as t
from typing import Type

from .airtable import AirtableRunner
from .base_runner import Runner
from .biomed import BiomedRunner
from .confluence import ConfluenceRunner
from .delta_table import DeltaTableRunner
from .discord import DiscordRunner
from .elasticsearch import ElasticSearchRunner
from .fsspec.azure import AzureRunner
from .fsspec.box import BoxRunner
from .fsspec.dropbox import DropboxRunner
from .fsspec.fsspec import FsspecRunner
from .fsspec.gcs import GCSRunner
from .fsspec.s3 import S3Runner
from .fsspec.sftp import SftpRunner
from .github import GithubRunner
from .gitlab import GitlabRunner
from .google_drive import GoogleDriveRunner
from .hubspot import HubSpotRunner
from .jira import JiraRunner
from .kafka import KafkaRunner
from .local import LocalRunner
from .mongodb import MongoDBRunner
from .notion import NotionRunner
from .onedrive import OneDriveRunner
from .opensearch import OpenSearchRunner
from .outlook import OutlookRunner
from .reddit import RedditRunner
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
    "hubspot": HubSpotRunner,
    "jira": JiraRunner,
    "kafka": KafkaRunner,
    "local": LocalRunner,
    "mongodb": MongoDBRunner,
    "notion": NotionRunner,
    "onedrive": OneDriveRunner,
    "opensearch": OpenSearchRunner,
    "outlook": OutlookRunner,
    "reddit": RedditRunner,
    "s3": S3Runner,
    "salesforce": SalesforceRunner,
    "sftp": SftpRunner,
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
    "KafkaRunner",
    "LocalRunner",
    "MongoDBRunner",
    "NotionRunner",
    "OneDriveRunner",
    "OpenSearchRunner",
    "OutlookRunner",
    "RedditRunner",
    "S3Runner",
    "SalesforceRunner",
    "SharePointRunner",
    "SlackRunner",
    "WikipediaRunner",
    "runner_map",
    "Runner",
]
