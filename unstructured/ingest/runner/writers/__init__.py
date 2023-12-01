import typing as t

from .azure import AzureWriter
from .azure_cognitive_search import AzureCognitiveSearchWriter
from .base_writer import Writer

writer_map: t.Dict[str, t.Type[Writer]] = {
    "azure": AzureWriter,
    "azure_cognitive_search": AzureCognitiveSearchWriter,
    # "box": box_writer,
    # "delta_table": delta_table_writer,
    # "dropbox": dropbox_writer,
    # "gcs": gcs_writer,
    # "mongodb": mongodb_writer,
    # "s3": s3_writer,
    # "pinecone": pinecone_writer,
    # "weaviate": weaviate_writer,
}

__all__ = ["writer_map"]
