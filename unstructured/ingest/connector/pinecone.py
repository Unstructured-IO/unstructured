import json
import typing as t
from dataclasses import dataclass

import pinecone.core.client.exceptions

from unstructured.ingest.error import DestinationConnectionError, WriteError
from unstructured.ingest.interfaces import (
    BaseConnectorConfig,
    BaseDestinationConnector,
    BaseIngestDoc,
    BaseSessionHandle,
    ConfigSessionHandleMixin,
    WriteConfig,
    WriteConfigSessionHandleMixin,
)
from unstructured.ingest.logger import logger
from unstructured.utils import requires_dependencies

# flake8: noqa E203


@requires_dependencies(["pinecone"], extras="pinecone")
def create_pinecone_object(api_key, index_name, environment):
    import pinecone

    pinecone.init(api_key=api_key, environment=environment)
    index = pinecone.Index(index_name)
    logger.debug(f"Connected to index: {pinecone.describe_index(index_name)}")
    return index


@dataclass
class PineconeSessionHandle(BaseSessionHandle):
    service: "Pinecone"


@dataclass
class PineconeWriteConfig(WriteConfigSessionHandleMixin, ConfigSessionHandleMixin, WriteConfig):
    api_key: str
    index_name: str
    environment: str
    # todo: fix buggy session handle implementation
    # with the bug, session handle gets created for each batch,
    # rather than with each process

    def create_session_handle(self) -> PineconeSessionHandle:
        service = create_pinecone_object(self.api_key, self.index_name, self.environment)
        return PineconeSessionHandle(service=service)

    def upsert_batch(self, batch):
        index = self.create_session_handle().service
        try:
            response = index.upsert(batch)
        except pinecone.core.client.exceptions.ApiException as api_error:
            raise WriteError(f"http error: {api_error}") from api_error
        logger.debug(f"results: {response}")


@dataclass
class SimplePineconeConfig(BaseConnectorConfig):
    api_key: str
    index_name: str
    environment: str


@dataclass
class PineconeDestinationConnector(BaseDestinationConnector):
    write_config: WriteConfig
    connector_config: SimplePineconeConfig

    @DestinationConnectionError.wrap
    @requires_dependencies(["pinecone"], extras="pinecone")
    def initialize(self):
        pass

    def write_dict(self, *args, dict_list: t.List[t.Dict[str, t.Any]], **kwargs) -> None:
        logger.info(
            f"Inserting / updating {len(dict_list)} documents to destination "
            f"index at {self.connector_config.index_name}",
        )
        import multiprocessing as mp

        num_processes = 1
        if num_processes == 1:
            for i in range(0, len(dict_list), 100):
                self.write_config.upsert_batch(dict_list[i : i + 100])

        else:
            with mp.Pool(
                processes=num_processes,
            ) as pool:
                pool.map(
                    self.write_config.upsert_batch,
                    [dict_list[i : i + 100] for i in range(0, len(dict_list), 100)],
                )

    def write(self, docs: t.List[BaseIngestDoc]) -> None:
        dict_list: t.List[t.Dict[str, t.Any]] = []
        for doc in docs:
            local_path = doc._output_filename
            with open(local_path) as json_file:
                dict_content = json.load(json_file)

                # assign element_id and embeddings to "id" and "values"
                # assign everything else to "metadata" field
                dict_content = [
                    {
                        "id": element.pop("element_id", None),
                        "values": element.pop("embeddings", None),
                        "metadata": {k: json.dumps(v) for k, v in element.items()},
                    }
                    for element in dict_content
                ]
                logger.info(
                    f"appending {len(dict_content)} json elements from content in {local_path}",
                )
                dict_list.extend(dict_content)
        self.write_dict(dict_list=dict_list)
