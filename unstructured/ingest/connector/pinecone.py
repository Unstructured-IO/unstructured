import copy
import json
import multiprocessing as mp
import typing as t
import uuid
from dataclasses import dataclass

from unstructured.ingest.enhanced_dataclass import enhanced_field
from unstructured.ingest.enhanced_dataclass.core import _asdict
from unstructured.ingest.error import DestinationConnectionError, WriteError
from unstructured.ingest.interfaces import (
    AccessConfig,
    BaseConnectorConfig,
    BaseDestinationConnector,
    ConfigSessionHandleMixin,
    IngestDocSessionHandleMixin,
    WriteConfig,
)
from unstructured.ingest.logger import logger
from unstructured.ingest.utils.data_prep import batch_generator
from unstructured.staging.base import flatten_dict
from unstructured.utils import requires_dependencies

if t.TYPE_CHECKING:
    from pinecone import Index as PineconeIndex


@dataclass
class PineconeAccessConfig(AccessConfig):
    api_key: str = enhanced_field(sensitive=True)


@dataclass
class SimplePineconeConfig(ConfigSessionHandleMixin, BaseConnectorConfig):
    index_name: str
    environment: str
    access_config: PineconeAccessConfig


@dataclass
class PineconeWriteConfig(WriteConfig):
    batch_size: int = 50
    num_processes: int = 1


@dataclass
class PineconeDestinationConnector(IngestDocSessionHandleMixin, BaseDestinationConnector):
    write_config: PineconeWriteConfig
    connector_config: SimplePineconeConfig
    _index: t.Optional["PineconeIndex"] = None

    def to_dict(self, **kwargs):
        """
        The _index variable in this dataclass breaks deepcopy due to:
        TypeError: cannot pickle '_thread.lock' object
        When serializing, remove it, meaning client data will need to be reinitialized
        when deserialized
        """
        self_cp = copy.copy(self)
        if hasattr(self_cp, "_index"):
            setattr(self_cp, "_index", None)
        return _asdict(self_cp, **kwargs)

    @property
    def pinecone_index(self):
        if self._index is None:
            self._index = self.create_index()
        return self._index

    def initialize(self):
        pass

    @requires_dependencies(["pinecone"], extras="pinecone")
    def create_index(self) -> "PineconeIndex":
        from pinecone import Pinecone

        from unstructured import __version__ as unstructured_version

        pc = Pinecone(
            api_key=self.connector_config.access_config.api_key,
            source_tag=f"unstructured=={unstructured_version}",
        )

        index = pc.Index(self.connector_config.index_name)
        logger.debug(f"Connected to index: {pc.describe_index(self.connector_config.index_name)}")
        return index

    @DestinationConnectionError.wrap
    def check_connection(self):
        _ = self.pinecone_index

    @DestinationConnectionError.wrap
    @requires_dependencies(["pinecone"], extras="pinecone")
    def upsert_batch(self, batch):
        import pinecone.core.client.exceptions

        index = self.pinecone_index
        try:
            response = index.upsert(batch)
        except pinecone.core.client.exceptions.ApiException as api_error:
            raise WriteError(f"http error: {api_error}") from api_error
        logger.debug(f"results: {response}")

    def write_dict(self, *args, elements_dict: t.List[t.Dict[str, t.Any]], **kwargs) -> None:
        logger.info(
            f"Upserting {len(elements_dict)} elements to destination "
            f"index at {self.connector_config.index_name}",
        )

        pinecone_batch_size = self.write_config.batch_size

        logger.info(f"using {self.write_config.num_processes} processes to upload")
        if self.write_config.num_processes == 1:
            for chunk in batch_generator(elements_dict, pinecone_batch_size):
                self.upsert_batch(chunk)  # noqa: E203

        else:
            with mp.Pool(
                processes=self.write_config.num_processes,
            ) as pool:
                pool.map(
                    self.upsert_batch, list(batch_generator(elements_dict, pinecone_batch_size))
                )

    def normalize_dict(self, element_dict: dict) -> dict:
        # While flatten_dict enables indexing on various fields,
        # element_serialized enables easily reloading the element object to memory.
        # element_serialized is formed without text/embeddings to avoid data bloating.
        return {
            "id": str(uuid.uuid4()),
            "values": element_dict.pop("embeddings", None),
            "metadata": {
                "text": element_dict.pop("text", None),
                "element_serialized": json.dumps(element_dict),
                **flatten_dict(
                    element_dict,
                    separator="-",
                    flatten_lists=True,
                    remove_none=True,
                ),
            },
        }
