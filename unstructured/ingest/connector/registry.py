import json
from typing import Dict, Type, cast

from dataclasses_json import DataClassJsonMixin

from unstructured.ingest.connector.airtable import AirtableIngestDoc
from unstructured.ingest.connector.azure import AzureBlobStorageIngestDoc
from unstructured.ingest.connector.biomed import BiomedIngestDoc
from unstructured.ingest.connector.box import BoxIngestDoc
from unstructured.ingest.connector.confluence import ConfluenceIngestDoc
from unstructured.ingest.connector.delta_table import DeltaTableIngestDoc
from unstructured.ingest.connector.discord import DiscordIngestDoc
from unstructured.ingest.connector.dropbox import DropboxIngestDoc
from unstructured.ingest.connector.elasticsearch import (
    ElasticsearchIngestDoc,
    ElasticsearchIngestDocBatch,
)
from unstructured.ingest.connector.gcs import GcsIngestDoc
from unstructured.ingest.connector.github import GitHubIngestDoc
from unstructured.ingest.connector.gitlab import GitLabIngestDoc
from unstructured.ingest.connector.google_drive import GoogleDriveIngestDoc
from unstructured.ingest.connector.hubspot import HubSpotIngestDoc
from unstructured.ingest.connector.jira import JiraIngestDoc
from unstructured.ingest.connector.local import LocalIngestDoc
from unstructured.ingest.connector.notion.connector import (
    NotionDatabaseIngestDoc,
    NotionPageIngestDoc,
)
from unstructured.ingest.connector.onedrive import OneDriveIngestDoc
from unstructured.ingest.connector.outlook import OutlookIngestDoc
from unstructured.ingest.connector.reddit import RedditIngestDoc
from unstructured.ingest.connector.s3 import S3IngestDoc
from unstructured.ingest.connector.salesforce import SalesforceIngestDoc
from unstructured.ingest.connector.sharepoint import SharepointIngestDoc
from unstructured.ingest.connector.slack import SlackIngestDoc
from unstructured.ingest.connector.wikipedia import (
    WikipediaIngestHTMLDoc,
    WikipediaIngestSummaryDoc,
    WikipediaIngestTextDoc,
)
from unstructured.ingest.interfaces import BaseIngestDoc

INGEST_DOC_NAME_TO_CLASS: Dict[str, Type[DataClassJsonMixin]] = {
    "airtable": AirtableIngestDoc,
    "azure": AzureBlobStorageIngestDoc,
    "biomed": BiomedIngestDoc,
    "box": BoxIngestDoc,
    "confluence": ConfluenceIngestDoc,
    "delta-table": DeltaTableIngestDoc,
    "discord": DiscordIngestDoc,
    "dropbox": DropboxIngestDoc,
    "elasticsearch": ElasticsearchIngestDoc,
    "elasticsearch_batch": ElasticsearchIngestDocBatch,
    "gcs": GcsIngestDoc,
    "github": GitHubIngestDoc,
    "gitlab": GitLabIngestDoc,
    "google_drive": GoogleDriveIngestDoc,
    "hubspot": HubSpotIngestDoc,
    "jira": JiraIngestDoc,
    "local": LocalIngestDoc,
    "notion_database": NotionDatabaseIngestDoc,
    "notion_page": NotionPageIngestDoc,
    "onedrive": OneDriveIngestDoc,
    "outlook": OutlookIngestDoc,
    "reddit": RedditIngestDoc,
    "s3": S3IngestDoc,
    "salesforce": SalesforceIngestDoc,
    "sharepoint": SharepointIngestDoc,
    "slack": SlackIngestDoc,
    "wikipedia_html": WikipediaIngestHTMLDoc,
    "wikipedia_text": WikipediaIngestTextDoc,
    "wikipedia_summary": WikipediaIngestSummaryDoc,
}


def create_ingest_doc_from_json(ingest_doc_json: str) -> BaseIngestDoc:
    try:
        ingest_doc_dict: dict = json.loads(ingest_doc_json)
    except TypeError as te:
        raise TypeError(
            f"failed to load json string when deserializing IngestDoc: {ingest_doc_json}",
        ) from te
    return create_ingest_doc_from_dict(ingest_doc_dict)


def create_ingest_doc_from_dict(ingest_doc_dict: dict) -> BaseIngestDoc:
    ingest_doc_dict = ingest_doc_dict.copy()
    if "registry_name" not in ingest_doc_dict:
        raise ValueError(f"registry_name not present in ingest doc: {ingest_doc_dict}")
    registry_name = ingest_doc_dict.pop("registry_name")
    try:
        ingest_doc_cls = INGEST_DOC_NAME_TO_CLASS[registry_name]
        return cast(BaseIngestDoc, ingest_doc_cls.from_dict(ingest_doc_dict))
    except KeyError:
        raise ValueError(
            f"Error: Received unknown IngestDoc name: {registry_name} while deserializing",
            "IngestDoc.",
        )
