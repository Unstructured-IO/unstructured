from __future__ import annotations

import unstructured.ingest.v2.processes.connectors.fsspec  # noqa: F401
from unstructured.ingest.v2.processes.connector_registry import (
    add_destination_entry,
    add_source_entry,
)

from .astra import CONNECTOR_TYPE as ASTRA_CONNECTOR_TYPE
from .astra import astra_destination_entry
from .chroma import CONNECTOR_TYPE as CHROMA_CONNECTOR_TYPE
from .chroma import chroma_destination_entry
from .databricks_volumes import CONNECTOR_TYPE as DATABRICKS_VOLUMES_CONNECTOR_TYPE
from .databricks_volumes import databricks_volumes_destination_entry
from .elasticsearch import CONNECTOR_TYPE as ELASTICSEARCH_CONNECTOR_TYPE
from .elasticsearch import elasticsearch_destination_entry, elasticsearch_source_entry
from .google_drive import CONNECTOR_TYPE as GOOGLE_DRIVE_CONNECTOR_TYPE
from .google_drive import google_drive_source_entry
from .local import CONNECTOR_TYPE as LOCAL_CONNECTOR_TYPE
from .local import local_destination_entry, local_source_entry
from .onedrive import CONNECTOR_TYPE as ONEDRIVE_CONNECTOR_TYPE
from .onedrive import onedrive_source_entry
from .opensearch import CONNECTOR_TYPE as OPENSEARCH_CONNECTOR_TYPE
from .opensearch import opensearch_destination_entry, opensearch_source_entry
from .sql import CONNECTOR_TYPE as SQL_CONNECTOR_TYPE
from .sql import sql_destination_entry
from .weaviate import CONNECTOR_TYPE as WEAVIATE_CONNECTOR_TYPE
from .weaviate import weaviate_destination_entry

add_destination_entry(destination_type=ASTRA_CONNECTOR_TYPE, entry=astra_destination_entry)

add_destination_entry(destination_type=CHROMA_CONNECTOR_TYPE, entry=chroma_destination_entry)

add_source_entry(source_type=ELASTICSEARCH_CONNECTOR_TYPE, entry=elasticsearch_source_entry)
add_destination_entry(
    destination_type=ELASTICSEARCH_CONNECTOR_TYPE, entry=elasticsearch_destination_entry
)

add_source_entry(source_type=GOOGLE_DRIVE_CONNECTOR_TYPE, entry=google_drive_source_entry)

add_source_entry(source_type=LOCAL_CONNECTOR_TYPE, entry=local_source_entry)
add_destination_entry(destination_type=LOCAL_CONNECTOR_TYPE, entry=local_destination_entry)

add_source_entry(source_type=ONEDRIVE_CONNECTOR_TYPE, entry=onedrive_source_entry)

add_source_entry(source_type=OPENSEARCH_CONNECTOR_TYPE, entry=opensearch_source_entry)
add_destination_entry(
    destination_type=OPENSEARCH_CONNECTOR_TYPE, entry=opensearch_destination_entry
)

add_destination_entry(destination_type=WEAVIATE_CONNECTOR_TYPE, entry=weaviate_destination_entry)

add_destination_entry(
    destination_type=DATABRICKS_VOLUMES_CONNECTOR_TYPE, entry=databricks_volumes_destination_entry
)

add_destination_entry(destination_type=SQL_CONNECTOR_TYPE, entry=sql_destination_entry)
