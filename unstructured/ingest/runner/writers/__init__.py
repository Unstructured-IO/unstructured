import typing as t

from .azure import AzureWriter
from .azure_cognitive_search import AzureCognitiveSearchWriter
from .base_writer import Writer
from .box import BoxWriter
from .delta_table import DeltaTableWriter
from .dropbox import DropboxWriter
from .gcs import GcsWriter
from .mongodb import MongodbWriter
from .pinecone import PineconeWriter
from .s3 import S3Writer
from .weaviate import WeaviateWriter

writer_map: t.Dict[str, t.Type[Writer]] = {
    "azure": AzureWriter,
    "azure_cognitive_search": AzureCognitiveSearchWriter,
    "box": BoxWriter,
    "delta_table": DeltaTableWriter,
    "dropbox": DropboxWriter,
    "gcs": GcsWriter,
    "mongodb": MongodbWriter,
    "pinecone": PineconeWriter,
    "s3": S3Writer,
    "weaviate": WeaviateWriter,
}

__all__ = ["writer_map"]
