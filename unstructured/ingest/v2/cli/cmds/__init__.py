from collections import Counter

import click

from .astra import astra_dest_cmd
from .chroma import chroma_dest_cmd
from .databricks_volumes import databricks_volumes_dest_cmd
from .elasticsearch import elasticsearch_dest_cmd, elasticsearch_src_cmd
from .fsspec.azure import azure_dest_cmd, azure_src_cmd
from .fsspec.box import box_dest_cmd, box_src_cmd
from .fsspec.dropbox import dropbox_dest_cmd, dropbox_src_cmd
from .fsspec.gcs import gcs_dest_cmd, gcs_src_cmd
from .fsspec.s3 import s3_dest_cmd, s3_src_cmd
from .fsspec.sftp import sftp_dest_cmd, sftp_src_cmd
from .google_drive import google_drive_src_cmd
from .local import local_dest_cmd, local_src_cmd
from .mongodb import mongodb_dest_cmd
from .onedrive import onedrive_drive_src_cmd
from .opensearch import opensearch_dest_cmd, opensearch_src_cmd
from .pinecone import pinecone_dest_cmd
from .singlestore import singlestore_dest_cmd
from .sql import sql_dest_cmd
from .weaviate import weaviate_dest_cmd

src_cmds = [
    azure_src_cmd,
    box_src_cmd,
    dropbox_src_cmd,
    elasticsearch_src_cmd,
    gcs_src_cmd,
    google_drive_src_cmd,
    local_src_cmd,
    onedrive_drive_src_cmd,
    opensearch_src_cmd,
    s3_src_cmd,
    sftp_src_cmd,
]
duplicate_src_names = [
    name for name, count in Counter([s.cmd_name for s in src_cmds]).items() if count > 1
]
if duplicate_src_names:
    raise ValueError(
        "the following source cmd names were reused, all must be unique: {}".format(
            ", ".join(duplicate_src_names)
        )
    )

dest_cmds = [
    astra_dest_cmd,
    azure_dest_cmd,
    box_dest_cmd,
    chroma_dest_cmd,
    dropbox_dest_cmd,
    elasticsearch_dest_cmd,
    gcs_dest_cmd,
    local_dest_cmd,
    opensearch_dest_cmd,
    pinecone_dest_cmd,
    s3_dest_cmd,
    sftp_dest_cmd,
    singlestore_dest_cmd,
    weaviate_dest_cmd,
    mongodb_dest_cmd,
    databricks_volumes_dest_cmd,
    sql_dest_cmd,
]

duplicate_dest_names = [
    name for name, count in Counter([d.cmd_name for d in dest_cmds]).items() if count > 1
]
if duplicate_dest_names:
    raise ValueError(
        "the following dest cmd names were reused, all must be unique: {}".format(
            ", ".join(duplicate_dest_names)
        )
    )


src: list[click.Group] = [v.get_cmd() for v in src_cmds]

dest: list[click.Command] = [v.get_cmd() for v in dest_cmds]
