from __future__ import annotations

from unstructured.ingest.v2.processes.connector_registry import (
    add_destination_entry,
    add_source_entry,
)

from .azure import CONNECTOR_TYPE as AZURE_CONNECTOR_TYPE
from .azure import azure_destination_entry, azure_source_entry
from .box import CONNECTOR_TYPE as BOX_CONNECTOR_TYPE
from .box import box_destination_entry, box_source_entry
from .dropbox import CONNECTOR_TYPE as DROPBOX_CONNECTOR_TYPE
from .dropbox import dropbox_destination_entry, dropbox_source_entry
from .gcs import CONNECTOR_TYPE as GCS_CONNECTOR_TYPE
from .gcs import gcs_destination_entry, gcs_source_entry
from .s3 import CONNECTOR_TYPE as S3_CONNECTOR_TYPE
from .s3 import s3_destination_entry, s3_source_entry
from .sftp import CONNECTOR_TYPE as SFTP_CONNECTOR_TYPE
from .sftp import sftp_destination_entry, sftp_source_entry

add_source_entry(source_type=AZURE_CONNECTOR_TYPE, entry=azure_source_entry)
add_destination_entry(destination_type=AZURE_CONNECTOR_TYPE, entry=azure_destination_entry)

add_source_entry(source_type=BOX_CONNECTOR_TYPE, entry=box_source_entry)
add_destination_entry(destination_type=BOX_CONNECTOR_TYPE, entry=box_destination_entry)

add_source_entry(source_type=DROPBOX_CONNECTOR_TYPE, entry=dropbox_source_entry)
add_destination_entry(destination_type=DROPBOX_CONNECTOR_TYPE, entry=dropbox_destination_entry)

add_source_entry(source_type=GCS_CONNECTOR_TYPE, entry=gcs_source_entry)
add_destination_entry(destination_type=GCS_CONNECTOR_TYPE, entry=gcs_destination_entry)

add_source_entry(source_type=S3_CONNECTOR_TYPE, entry=s3_source_entry)
add_destination_entry(destination_type=S3_CONNECTOR_TYPE, entry=s3_destination_entry)

add_source_entry(source_type=SFTP_CONNECTOR_TYPE, entry=sftp_source_entry)
add_destination_entry(destination_type=SFTP_CONNECTOR_TYPE, entry=sftp_destination_entry)
