import json
import multiprocessing as mp
import typing as t
import uuid
from dataclasses import dataclass

from unstructured.ingest.enhanced_dataclass import enhanced_field
from unstructured.ingest.error import DestinationConnectionError, WriteError
from unstructured.ingest.interfaces import (
    AccessConfig,
    BaseConnectorConfig,
    BaseDestinationConnector,
    BaseIngestDoc,
    ConfigSessionHandleMixin,
    IngestDocSessionHandleMixin,
    WriteConfig,
)
from unstructured.ingest.logger import logger
from unstructured.ingest.utils.data_prep import chunk_generator
from unstructured.staging.base import flatten_dict
from unstructured.utils import requires_dependencies

if t.TYPE_CHECKING:
    from qdrant_client import QdrantClient


@dataclass
class QdrantAccessConfig(AccessConfig):
    api_key: t.Optional[str] = enhanced_field(sensitive=True)


@dataclass
class SimpleQdrantConfig(ConfigSessionHandleMixin, BaseConnectorConfig):
    collection_name: str
    location: t.Optional[str] = None
    url: t.Optional[str] = None
    port: t.Optional[int] = 6333
    grpc_port: t.Optional[int] = 6334
    prefer_grpc: t.Optional[bool] = False
    https: t.Optional[bool] = None
    prefix: t.Optional[str] = None
    timeout: t.Optional[float] = None
    host: t.Optional[str] = None
    path: t.Optional[str] = None
    force_disable_check_same_thread: t.Optional[bool] = False
    access_config: t.Optional[QdrantAccessConfig] = None


@dataclass
class QdrantWriteConfig(WriteConfig):
    batch_size: int = 50
    num_processes: int = 1


@dataclass
class QdrantDestinationConnector(IngestDocSessionHandleMixin, BaseDestinationConnector):
    write_config: QdrantWriteConfig
    connector_config: SimpleQdrantConfig
    _client: t.Optional["QdrantClient"] = None

    @property
    def qdrant_client(self):
        if self._client is None:
            self._client = self.create_client()
        return self._client

    def initialize(self):
        ...

    @requires_dependencies(["qdrant_client"], extras="qdrant")
    def create_client(self) -> "QdrantClient":
        from qdrant_client import QdrantClient

        client = QdrantClient(
            location=self.connector_config.location,
            url=self.connector_config.url,
            port=self.connector_config.port,
            grpc_port=self.connector_config.grpc_port,
            prefer_grpc=self.connector_config.prefer_grpc,
            https=self.connector_config.https,
            api_key=self.connector_config.access_config.api_key
            if self.connector_config.access_config
            else None,
            prefix=self.connector_config.prefix,
            timeout=self.connector_config.timeout,
            host=self.connector_config.host,
            path=self.connector_config.path,
            force_disable_check_same_thread=self.connector_config.force_disable_check_same_thread,
        )

        return client

    @DestinationConnectionError.wrap
    def check_connection(self):
        self.qdrant_client.get_collections()

    @DestinationConnectionError.wrap
    @requires_dependencies(["qdrant_client"], extras="qdrant")
    def upsert_batch(self, batch: t.List[t.Dict[str, t.Any]]):
        from qdrant_client import models

        client = self.qdrant_client
        try:
            points: list[models.PointStruct] = [models.PointStruct(**item) for item in batch]
            response = client.upsert(
                self.connector_config.collection_name, points=points, wait=True
            )
        except Exception as api_error:
            raise WriteError(f"Qdrant error: {api_error}") from api_error
        logger.debug(f"results: {response}")

    def write_dict(self, *args, dict_list: t.List[t.Dict[str, t.Any]], **kwargs) -> None:
        logger.info(
            f"Upserting {len(dict_list)} elements to " f"{self.connector_config.collection_name}",
        )

        qdrant_batch_size = self.write_config.batch_size

        logger.info(f"using {self.write_config.num_processes} processes to upload")
        if self.write_config.num_processes == 1:
            for chunk in chunk_generator(dict_list, qdrant_batch_size):
                self.upsert_batch(chunk)

        else:
            with mp.Pool(
                processes=self.write_config.num_processes,
            ) as pool:
                pool.map(self.upsert_batch, list(chunk_generator(dict_list, qdrant_batch_size)))

    def write(self, docs: t.List[BaseIngestDoc]) -> None:
        dict_list: t.List[t.Dict[str, t.Any]] = []
        for doc in docs:
            local_path = doc._output_filename
            with open(local_path) as json_file:
                dict_content = json.load(json_file)
                dict_content = [
                    {
                        "id": str(uuid.uuid4()),
                        "vector": element.pop("embeddings", {}),
                        "payload": {
                            "text": element.pop("text", None),
                            "element_serialized": json.dumps(element),
                            **flatten_dict(
                                element,
                                separator="-",
                                flatten_lists=True,
                            ),
                        },
                    }
                    for element in dict_content
                ]
                logger.info(
                    f"appending {len(dict_content)} json elements from content in {local_path}",
                )
                dict_list.extend(dict_content)
        self.write_dict(dict_list=dict_list)
