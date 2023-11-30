import json
import multiprocessing as mp
import typing as t
import uuid
from dataclasses import dataclass

from unstructured.ingest.error import DestinationConnectionError, WriteError
from unstructured.ingest.interfaces import (
    BaseConnectorConfig,
    BaseDestinationConnector,
    BaseIngestDoc,
    BaseSessionHandle,
    ConfigSessionHandleMixin,
    IngestDocSessionHandleMixin,
    WriteConfig,
)
from unstructured.ingest.logger import logger
from unstructured.staging.base import flatten_dict
from unstructured.utils import requires_dependencies

if t.TYPE_CHECKING:
    from pinecone import Index as PineconeIndex


@dataclass
class PineconeSessionHandle(BaseSessionHandle):
    service: "PineconeIndex"


@DestinationConnectionError.wrap
@requires_dependencies(["pinecone"], extras="pinecone")
def create_pinecone_object(api_key, index_name, environment):
    import pinecone

    pinecone.init(api_key=api_key, environment=environment)
    index = pinecone.Index(index_name)
    logger.debug(f"Connected to index: {pinecone.describe_index(index_name)}")
    return index


@dataclass
class SimplePineconeConfig(ConfigSessionHandleMixin, BaseConnectorConfig):
    api_key: str
    index_name: str
    environment: str

    def create_session_handle(self) -> PineconeSessionHandle:
        service = create_pinecone_object(self.api_key, self.index_name, self.environment)
        return PineconeSessionHandle(service=service)


@dataclass
class PineconeWriteConfig(IngestDocSessionHandleMixin, WriteConfig):
    connector_config: SimplePineconeConfig
    batch_size: int = 50
    num_processes: int = 1


@dataclass
class PineconeDestinationConnector(BaseDestinationConnector):
    write_config: PineconeWriteConfig
    connector_config: SimplePineconeConfig

    def initialize(self):
        pass

    @DestinationConnectionError.wrap
    def check_connection(self):
        create_pinecone_object(
            self.connector_config.api_key,
            self.connector_config.index_name,
            self.connector_config.environment,
        )

    @DestinationConnectionError.wrap
    @requires_dependencies(["pinecone"], extras="pinecone")
    def upsert_batch(self, batch):
        import pinecone.core.client.exceptions

        self.write_config.global_session()

        index = self.write_config.session_handle.service
        try:
            response = index.upsert(batch)
        except pinecone.core.client.exceptions.ApiException as api_error:
            raise WriteError(f"http error: {api_error}") from api_error
        logger.debug(f"results: {response}")

    def write_dict(self, *args, dict_list: t.List[t.Dict[str, t.Any]], **kwargs) -> None:
        logger.info(
            f"Upserting {len(dict_list)} elements to destination "
            f"index at {self.connector_config.index_name}",
        )

        pinecone_batch_size = self.write_config.batch_size

        logger.info(f"using {self.write_config.num_processes} processes to upload")
        if self.write_config.num_processes == 1:
            for i in range(0, len(dict_list), pinecone_batch_size):
                self.upsert_batch(dict_list[i : i + pinecone_batch_size])  # noqa: E203

        else:
            with mp.Pool(
                processes=self.write_config.num_processes,
            ) as pool:
                pool.map(
                    self.upsert_batch,
                    [
                        dict_list[i : i + pinecone_batch_size]  # noqa: E203
                        for i in range(0, len(dict_list), pinecone_batch_size)
                    ],  # noqa: E203
                )

    def write(self, docs: t.List[BaseIngestDoc]) -> None:
        dict_list: t.List[t.Dict[str, t.Any]] = []
        for doc in docs:
            local_path = doc._output_filename
            with open(local_path) as json_file:
                dict_content = json.load(json_file)

                # we assign embeddings to "values", and other fields to "metadata"
                dict_content = [
                    # While flatten_dict enables indexing on various fields,
                    # element_serialized enables easily reloading the element object to memory.
                    # element_serialized is formed without text/embeddings to avoid data bloating.
                    {
                        "id": str(uuid.uuid4()),
                        "values": element.pop("embeddings", None),
                        "metadata": {
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
