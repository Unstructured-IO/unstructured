import typing as t

from .astra import AstraWriter
from .azure_cognitive_search import AzureCognitiveSearchWriter
from .base_writer import Writer
from .chroma import ChromaWriter
from .clarifai import ClarifaiWriter
from .databricks_volumes import DatabricksVolumesWriter
from .delta_table import DeltaTableWriter
from .elasticsearch import ElasticsearchWriter
from .fsspec.azure import AzureWriter
from .fsspec.box import BoxWriter
from .fsspec.dropbox import DropboxWriter
from .fsspec.gcs import GcsWriter
from .fsspec.s3 import S3Writer
from .mongodb import MongodbWriter
from .opensearch import OpenSearchWriter
from .pinecone import PineconeWriter
from .qdrant import QdrantWriter
from .sql import SqlWriter
from .vectara import VectaraWriter
from .weaviate import WeaviateWriter

writer_map: t.Dict[str, t.Type[Writer]] = {
    "astra": AstraWriter,
    "azure": AzureWriter,
    "azure_cognitive_search": AzureCognitiveSearchWriter,
    "box": BoxWriter,
    "chroma": ChromaWriter,
    "clarifai": ClarifaiWriter,
    "databricks_volumes": DatabricksVolumesWriter,
    "delta_table": DeltaTableWriter,
    "dropbox": DropboxWriter,
    "elasticsearch": ElasticsearchWriter,
    "gcs": GcsWriter,
    "mongodb": MongodbWriter,
    "opensearch": OpenSearchWriter,
    "pinecone": PineconeWriter,
    "qdrant": QdrantWriter,
    "s3": S3Writer,
    "sql": SqlWriter,
    "vectara": VectaraWriter,
    "weaviate": WeaviateWriter,
}

__all__ = ["writer_map"]
