from typing import t

from .azure_cognitive_search import azure_cognitive_search_writer
from .delta_table import delta_table_writer
from .s3 import s3_writer

writer_map: t.Dict[str, t.Callable] = {
    "s3": s3_writer,
    "delta_table": delta_table_writer,
    "azure_cognitive_search": azure_cognitive_search_writer,
}

__all__ = ["writer_map"]
