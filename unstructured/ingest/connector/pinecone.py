import json
import typing as t
from dataclasses import dataclass

import pinecone.core.client.exceptions

from unstructured.ingest.error import DestinationConnectionError, WriteError
from unstructured.ingest.interfaces import (
    BaseConnectorConfig,
    BaseDestinationConnector,
    BaseIngestDoc,
    WriteConfig,
)
from unstructured.ingest.logger import logger
from unstructured.utils import requires_dependencies


@dataclass
class SimplePineconeConfig(BaseConnectorConfig):
    api_key: str
    index_name: str
    environment: str


@dataclass
class PineconeWriteConfig(WriteConfig):
    api_key: str
    index_name: str
    environment: str


# When upserting larger amounts of data, upsert data in batches of 100 vectors
# or fewer over multiple upsert requests.
@dataclass
class PineconeDestinationConnector(BaseDestinationConnector):
    write_config: WriteConfig
    connector_config: SimplePineconeConfig

    @DestinationConnectionError.wrap
    @requires_dependencies(["pinecone-client"], extras="pinecone")
    def initialize(self):
        import pinecone

        pinecone.init(
            api_key=self.connector_config.api_key,
            environment=self.connector_config.environment,
        )

        self.index = pinecone.Index(self.connector_config.index_name)

        print("Connected to index:", pinecone.describe_index(self.connector_config.index_name))

    def write_dict(self, *args, json_list: t.List[t.Dict[str, t.Any]], **kwargs) -> None:
        logger.info(
            f"Inserting / updating {len(json_list)} documents to destination "
            f"index at {self.connector_config.index_name}",
        )
        try:
            response = self.index.upsert(documents=json_list)

        except pinecone.core.client.exceptions.ApiException as api_error:
            raise WriteError(f"http error: {api_error}") from api_error

        logger.debug(f"results: {response}")

    def write(self, docs: t.List[BaseIngestDoc]) -> None:
        json_list: t.List[t.Dict[str, t.Any]] = []
        for doc in docs:
            local_path = doc._output_filename
            with open(local_path) as json_file:
                json_content = json.load(json_file)
                for content in json_content:
                    self.conform_dict(data=content)
                logger.info(
                    f"appending {len(json_content)} json elements from content in {local_path}",
                )
                json_list.extend(json_content)
        self.write_dict(json_list=json_list)
