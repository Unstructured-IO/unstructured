import typing as t

from .azure import azure_writer
from .azure_cognitive_search import azure_cognitive_search_writer
from .box import box_writer
from .delta_table import delta_table_writer
from .dropbox import dropbox_writer
from .gcs import gcs_writer
from .mongodb import mongodb_writer
from .pinecone import pinecone_writer
from .s3 import s3_writer

writer_map: t.Dict[str, t.Callable] = {
    "azure": azure_writer,
    "azure_cognitive_search": azure_cognitive_search_writer,
    "box": box_writer,
    "delta_table": delta_table_writer,
    "dropbox": dropbox_writer,
    "gcs": gcs_writer,
    "mongodb": mongodb_writer,
    "s3": s3_writer,
    "pinecone": pinecone_writer,
}

__all__ = ["writer_map"]
