import json
import multiprocessing as mp
import typing as t
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


@dataclass
class PineconeSessionHandle(BaseSessionHandle):
    service: "pinecone.Index"  # noqa: F821


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

    def check_connection(self):
        pass

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

    def select_fields_from_element(
        self, element: t.Dict, fields: t.List[str] = ["text", "metadata"]
    ) -> t.Dict:
        return {key: element[key] for key in fields if key in element}

    def write(self, docs: t.List[BaseIngestDoc]) -> None:
        dict_list: t.List[t.Dict[str, t.Any]] = []
        for doc in docs:
            local_path = doc._output_filename
            with open(local_path) as json_file:
                dict_content = json.load(json_file)

                # assign element_id to "id", embeddings to "values", and other fields to "metadata"
                dict_content = [
                    {
                        "id": element.pop("element_id", None),
                        "values": element.pop("embeddings", None),
                        "metadata": {
                            # Since pinecone does not allow lists of any type other than str,
                            # we dump list objects (parsing them to str) wherever we see them.
                            k: (
                                v
                                if not isinstance(v, list)
                                else [json.dumps(list_item) for list_item in v]
                            )
                            for k, v in flatten_dict(
                                self.select_fields_from_element(
                                    element, fields=["text", "metadata"]
                                ),
                                separator="-",
                            ).items()
                        },
                    }
                    for element in dict_content
                ]
                logger.info(
                    f"appending {len(dict_content)} json elements from content in {local_path}",
                )
                dict_list.extend(dict_content)
        self.write_dict(dict_list=dict_list)
