from __future__ import annotations

import collections
import typing as t

from unstructured.ingest.cli.base.src import BaseSrcCmd
from unstructured.ingest.cli.cmds.fsspec.sftp import get_base_src_cmd as sftp_base_src_cmd

from .airtable import get_base_src_cmd as airtable_base_src_cmd
from .astra import get_base_dest_cmd as astra_base_dest_cmd
from .azure_cognitive_search import get_base_dest_cmd as azure_cognitive_search_base_dest_cmd
from .biomed import get_base_src_cmd as biomed_base_src_cmd
from .chroma import get_base_dest_cmd as chroma_base_dest_cmd
from .confluence import get_base_src_cmd as confluence_base_src_cmd
from .databricks_volumes import get_base_dest_cmd as databricks_volumes_dest_cmd
from .delta_table import get_base_dest_cmd as delta_table_dest_cmd
from .delta_table import get_base_src_cmd as delta_table_base_src_cmd
from .discord import get_base_src_cmd as discord_base_src_cmd
from .elasticsearch import get_base_dest_cmd as elasticsearch_base_dest_cmd
from .elasticsearch import get_base_src_cmd as elasticsearch_base_src_cmd
from .fsspec.azure import get_base_dest_cmd as azure_base_dest_cmd
from .fsspec.azure import get_base_src_cmd as azure_base_src_cmd
from .fsspec.box import get_base_dest_cmd as box_base_dest_cmd
from .fsspec.box import get_base_src_cmd as box_base_src_cmd
from .fsspec.dropbox import get_base_dest_cmd as dropbox_base_dest_cmd
from .fsspec.dropbox import get_base_src_cmd as dropbox_base_src_cmd
from .fsspec.fsspec import get_base_dest_cmd as fsspec_base_dest_cmd
from .fsspec.fsspec import get_base_src_cmd as fsspec_base_src_cmd
from .fsspec.gcs import get_base_dest_cmd as gcs_base_dest_cmd
from .fsspec.gcs import get_base_src_cmd as gcs_base_src_cmd
from .fsspec.s3 import get_base_dest_cmd as s3_base_dest_cmd
from .fsspec.s3 import get_base_src_cmd as s3_base_src_cmd
from .github import get_base_src_cmd as github_base_src_cmd
from .gitlab import get_base_src_cmd as gitlab_base_src_cmd
from .google_drive import get_base_src_cmd as google_drive_base_src_cmd
from .hubspot import get_base_src_cmd as hubspot_base_src_cmd
from .jira import get_base_src_cmd as jira_base_src_cmd
from .local import get_base_src_cmd as local_base_src_cmd
from .mongodb import get_base_dest_cmd as mongo_base_dest_cmd
from .mongodb import get_base_src_cmd as mongodb_base_src_cmd
from .notion import get_base_src_cmd as notion_base_src_cmd
from .onedrive import get_base_src_cmd as onedrive_base_src_cmd
from .opensearch import get_base_dest_cmd as opensearch_base_dest_cmd
from .opensearch import get_base_src_cmd as opensearch_base_src_cmd
from .outlook import get_base_src_cmd as outlook_base_src_cmd
from .pinecone import get_base_dest_cmd as pinecone_base_dest_cmd
from .qdrant import get_base_dest_cmd as qdrant_base_dest_cmd
from .reddit import get_base_src_cmd as reddit_base_src_cmd
from .salesforce import get_base_src_cmd as salesforce_base_src_cmd
from .sharepoint import get_base_src_cmd as sharepoint_base_src_cmd
from .slack import get_base_src_cmd as slack_base_src_cmd
from .sql import get_base_dest_cmd as sql_base_dest_cmd
from .vectara import get_base_dest_cmd as vectara_base_dest_cmd
from .weaviate import get_base_dest_cmd as weaviate_dest_cmd
from .wikipedia import get_base_src_cmd as wikipedia_base_src_cmd

if t.TYPE_CHECKING:
    from unstructured.ingest.cli.base.dest import BaseDestCmd

base_src_cmd_fns: t.List[t.Callable[[], BaseSrcCmd]] = [
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
    hubspot_base_src_cmd,
    jira_base_src_cmd,
    local_base_src_cmd,
    mongodb_base_src_cmd,
    notion_base_src_cmd,
    onedrive_base_src_cmd,
    opensearch_base_src_cmd,
    outlook_base_src_cmd,
    reddit_base_src_cmd,
    salesforce_base_src_cmd,
    sftp_base_src_cmd,
    sharepoint_base_src_cmd,
    slack_base_src_cmd,
    s3_base_src_cmd,
    wikipedia_base_src_cmd,
]

# Make sure there are not overlapping names
src_cmd_names = [b().cmd_name for b in base_src_cmd_fns]
src_duplicates = [item for item, count in collections.Counter(src_cmd_names).items() if count > 1]
if src_duplicates:
    raise ValueError(
        "multiple base src commands defined with the same names: {}".format(
            ", ".join(src_duplicates),
        ),
    )

base_dest_cmd_fns: t.List[t.Callable[[], "BaseDestCmd"]] = [
    astra_base_dest_cmd,
    azure_base_dest_cmd,
    box_base_dest_cmd,
    chroma_base_dest_cmd,
    databricks_volumes_dest_cmd,
    dropbox_base_dest_cmd,
    elasticsearch_base_dest_cmd,
    fsspec_base_dest_cmd,
    gcs_base_dest_cmd,
    s3_base_dest_cmd,
    azure_cognitive_search_base_dest_cmd,
    delta_table_dest_cmd,
    sql_base_dest_cmd,
    weaviate_dest_cmd,
    mongo_base_dest_cmd,
    pinecone_base_dest_cmd,
    qdrant_base_dest_cmd,
    opensearch_base_dest_cmd,
    vectara_base_dest_cmd,
]

# Make sure there are not overlapping names
dest_cmd_names = [b().cmd_name for b in base_dest_cmd_fns]
dest_duplicates = [item for item, count in collections.Counter(dest_cmd_names).items() if count > 1]
if dest_duplicates:
    raise ValueError(
        "multiple base dest commands defined with the same names: {}".format(
            ", ".join(dest_duplicates),
        ),
    )

__all__ = [
    "base_src_cmd_fns",
    "base_dest_cmd_fns",
]
