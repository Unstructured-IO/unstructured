import typing as t

from .azure_cognitive_search import AzureCognitiveSearchWriter
from .base_writer import Writer
from .chroma import ChromaWriter
from .delta_table import DeltaTableWriter
from .elasticsearch import ElasticsearchWriter
from .fsspec.azure import AzureWriter
from .fsspec.box import BoxWriter
from .fsspec.dropbox import DropboxWriter
from .fsspec.gcs import GcsWriter
from .fsspec.s3 import S3Writer
from .mongodb import MongodbWriter
from .pinecone import PineconeWriter
from .qdrant import QdrantWriter
from .weaviate import WeaviateWriter

writer_map: t.Dict[str, t.Type[Writer]] = {
    "azure": AzureWriter,
    "azure_cognitive_search": AzureCognitiveSearchWriter,
    "box": BoxWriter,
    "chroma": ChromaWriter,
    "delta_table": DeltaTableWriter,
    "dropbox": DropboxWriter,
    "elasticsearch": ElasticsearchWriter,
    "gcs": GcsWriter,
    "mongodb": MongodbWriter,
    "pinecone": PineconeWriter,
    "qdrant": QdrantWriter,
    "s3": S3Writer,
    "weaviate": WeaviateWriter,
}

__all__ = ["writer_map"]
