import copy
import typing as t
from dataclasses import dataclass, field

from unstructured.ingest.enhanced_dataclass import enhanced_field
from unstructured.ingest.enhanced_dataclass.core import _asdict
from unstructured.ingest.error import DestinationConnectionError, SourceConnectionNetworkError
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
    from astrapy.db import AstraDB, AstraDBCollection

NON_INDEXED_FIELDS = ["metadata._node_content", "content"]


@dataclass
class AstraAccessConfig(AccessConfig):
    token: t.Optional[str] = enhanced_field(default=None, sensitive=True)
    api_endpoint: t.Optional[str] = enhanced_field(default=None, sensitive=True)


@dataclass
class SimpleAstraConfig(BaseConnectorConfig):
    access_config: AstraAccessConfig
    collection_name: str
    embedding_dimension: int


@dataclass
class AstraWriteConfig(WriteConfig):
    batch_size: int = 20


@dataclass
class AstraDestinationConnector(BaseDestinationConnector):
    write_config: AstraWriteConfig
    connector_config: SimpleAstraConfig
    _astra_db: t.Optional["AstraDB"] = field(init=False, default=None)
    _astra_db_collection: t.Optional["AstraDBCollection"] = field(init=False, default=None)

    def to_dict(self, **kwargs):
        """
        The _astra_db_collection variable in this dataclass breaks deepcopy due to:
        TypeError: cannot pickle '_thread.lock' object
        When serializing, remove it, meaning client data will need to be reinitialized
        when deserialized
        """
        self_cp = copy.copy(self)

        if hasattr(self_cp, "_astra_db_collection"):
            setattr(self_cp, "_astra_db_collection", None)

        return _asdict(self_cp, **kwargs)

    @property
    @requires_dependencies(["astrapy"], extras="astra")
    def astra_db_collection(self) -> "AstraDBCollection":
        if self._astra_db_collection is None:
            from astrapy.db import AstraDB

            # Build the Astra DB object
            self._astra_db = AstraDB(
                api_endpoint=self.connector_config.access_config.api_endpoint,
                token=self.connector_config.access_config.token,
            )

            # Create and connect to the newly created collection
            self._astra_db_collection = self._astra_db.create_collection(
                collection_name=self.connector_config.collection_name,
                dimension=self.connector_config.embedding_dimension,
                options={"indexing": {"deny": NON_INDEXED_FIELDS}},
            )
        return self._astra_db_collection

    @requires_dependencies(["astrapy"], extras="astra")
    @DestinationConnectionError.wrap
    def initialize(self):
        _ = self.astra_db_collection

    @requires_dependencies(["astrapy"], extras="astra")
    def check_connection(self):
        try:
            _ = self.astra_db_collection
        except Exception as e:
            logger.error(f"Failed to validate connection {e}", exc_info=True)
            raise SourceConnectionNetworkError(f"failed to validate connection: {e}")

    def write_dict(self, *args, elements_dict: t.List[t.Dict[str, t.Any]], **kwargs) -> None:
        logger.info(f"Inserting / updating {len(elements_dict)} documents to Astra.")

        astra_batch_size = self.write_config.batch_size

        for chunk in chunk_generator(elements_dict, astra_batch_size):
            self._astra_db_collection.insert_many(chunk)

    def normalize_dict(self, element_dict: dict) -> dict:
        return {
            "$vector": element_dict.pop("embeddings", None),
            "content": element_dict.pop("text", None),
            "metadata": flatten_dict(
                element_dict, separator="-", flatten_lists=True, remove_none=True
            ),
        }
