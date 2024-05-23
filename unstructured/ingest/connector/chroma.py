import copy
import typing as t
import uuid
from dataclasses import dataclass

from unstructured.ingest.enhanced_dataclass.core import _asdict
from unstructured.ingest.error import DestinationConnectionError
from unstructured.ingest.interfaces import (
    AccessConfig,
    BaseConnectorConfig,
    BaseDestinationConnector,
    WriteConfig,
)
from unstructured.ingest.logger import logger
from unstructured.ingest.utils.data_prep import chunk_generator
from unstructured.staging.base import flatten_dict
from unstructured.utils import requires_dependencies

if t.TYPE_CHECKING:
    from chromadb import Collection as ChromaCollection


@dataclass
class ChromaAccessConfig(AccessConfig):
    settings: t.Optional[t.Dict[str, str]] = None
    headers: t.Optional[t.Dict[str, str]] = None


@dataclass
class SimpleChromaConfig(BaseConnectorConfig):
    access_config: ChromaAccessConfig
    collection_name: str
    path: t.Optional[str] = None
    tenant: t.Optional[str] = "default_tenant"
    database: t.Optional[str] = "default_database"
    host: t.Optional[str] = None
    port: t.Optional[int] = None
    ssl: bool = False


@dataclass
class ChromaWriteConfig(WriteConfig):
    batch_size: int = 100


@dataclass
class ChromaDestinationConnector(BaseDestinationConnector):
    write_config: ChromaWriteConfig
    connector_config: SimpleChromaConfig
    _collection: t.Optional["ChromaCollection"] = None

    @property
    def chroma_collection(self):
        if self._collection is None:
            self._collection = self.create_collection()
        return self._collection

    def initialize(self):
        pass

    @DestinationConnectionError.wrap
    def check_connection(self):
        _ = self.chroma_collection

    def to_dict(self, **kwargs):
        """
        The _collection variable in this dataclass breaks deepcopy due to:
        TypeError: cannot pickle 'module' object
        When serializing, remove it, meaning collection data will need to be reinitialized
        when deserialized
        """
        self_cp = copy.copy(self)
        if hasattr(self_cp, "_collection"):
            setattr(self_cp, "_collection", None)
        return _asdict(self_cp, **kwargs)

    @requires_dependencies(["chromadb"], extras="chroma")
    def create_collection(self) -> "ChromaCollection":
        import chromadb

        if self.connector_config.path:
            chroma_client = chromadb.PersistentClient(
                path=self.connector_config.path,
                settings=self.connector_config.settings,
                tenant=self.connector_config.tenant,
                database=self.connector_config.database,
            )

        elif self.connector_config.host and self.connector_config.port:
            chroma_client = chromadb.HttpClient(
                host=self.connector_config.host,
                port=self.connector_config.port,
                ssl=self.connector_config.ssl,
                headers=self.connector_config.access_config.headers,
                settings=self.connector_config.access_config.settings,
                tenant=self.connector_config.tenant,
                database=self.connector_config.database,
            )
        else:
            raise ValueError("Chroma connector requires either path or host and port to be set.")

        collection = chroma_client.get_or_create_collection(
            name=self.connector_config.collection_name
        )
        return collection

    @DestinationConnectionError.wrap
    @requires_dependencies(["chromadb"], extras="chroma")
    def upsert_batch(self, batch):
        collection = self.chroma_collection

        try:
            # Chroma wants lists even if there is only one element
            # Upserting to prevent duplicates
            collection.upsert(
                ids=batch["ids"],
                documents=batch["documents"],
                embeddings=batch["embeddings"],
                metadatas=batch["metadatas"],
            )
        except Exception as e:
            raise ValueError(f"chroma error: {e}") from e

    @staticmethod
    def prepare_chroma_list(chunk: t.Tuple[t.Dict[str, t.Any]]) -> t.Dict[str, t.List[t.Any]]:
        """Helper function to break a tuple of dicts into list of parallel lists for ChromaDb.
        ({'id':1}, {'id':2}, {'id':3}) -> {'ids':[1,2,3]}"""
        chroma_dict = {}
        chroma_dict["ids"] = [x.get("id") for x in chunk]
        chroma_dict["documents"] = [x.get("document") for x in chunk]
        chroma_dict["embeddings"] = [x.get("embedding") for x in chunk]
        chroma_dict["metadatas"] = [x.get("metadata") for x in chunk]
        # Make sure all lists are of the same length
        assert (
            len(chroma_dict["ids"])
            == len(chroma_dict["documents"])
            == len(chroma_dict["embeddings"])
            == len(chroma_dict["metadatas"])
        )
        return chroma_dict

    def write_dict(self, *args, elements_dict: t.List[t.Dict[str, t.Any]], **kwargs) -> None:
        logger.info(f"Inserting / updating {len(elements_dict)} documents to destination ")

        chroma_batch_size = self.write_config.batch_size

        for chunk in chunk_generator(elements_dict, chroma_batch_size):
            self.upsert_batch(self.prepare_chroma_list(chunk))

    def normalize_dict(self, element_dict: dict) -> dict:
        element_id = element_dict.get("element_id", str(uuid.uuid4()))
        return {
            "id": element_id,
            "embedding": element_dict.pop("embeddings", None),
            "document": element_dict.pop("text", None),
            "metadata": flatten_dict(
                element_dict, separator="-", flatten_lists=True, remove_none=True
            ),
        }
