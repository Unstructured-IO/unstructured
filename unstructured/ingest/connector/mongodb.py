import json
import typing as t
from dataclasses import dataclass, field

from unstructured.ingest.error import DestinationConnectionError, WriteError
from unstructured.ingest.interfaces import (
    BaseConnectorConfig,
    BaseDestinationConnector,
    BaseSingleIngestDoc,
    WriteConfig,
)
from unstructured.ingest.logger import logger
from unstructured.utils import requires_dependencies

if t.TYPE_CHECKING:
    from pymongo import MongoClient


SERVER_API_VERSION = "1"


@dataclass
class SimpleMongoDBStorageConfig(BaseConnectorConfig):
    uri: t.Optional[str] = None
    host: t.Optional[str] = None
    port: int = 27017
    client_params: t.Dict[str, t.Any] = field(default_factory=dict)


@dataclass
class MongoDBWriteConfig(WriteConfig):
    database: str
    collection: str


@dataclass
class MongoDBDestinationConnector(BaseDestinationConnector):
    write_config: MongoDBWriteConfig
    connector_config: SimpleMongoDBStorageConfig
    _client: t.Optional["MongoClient"] = field(init=False, default=None)

    @requires_dependencies(["pymongo"], extras="mongodb")
    def generate_client(self) -> "MongoClient":
        from pymongo import MongoClient
        from pymongo.server_api import ServerApi

        if self.connector_config.uri:
            return MongoClient(
                self.connector_config.uri,
                server_api=ServerApi(version=SERVER_API_VERSION),
                **self.connector_config.client_params,
            )
        else:
            return MongoClient(
                host=self.connector_config.host,
                port=self.connector_config.port,
                server_api=ServerApi(version=SERVER_API_VERSION),
                **self.connector_config.client_params,
            )

    @property
    def client(self) -> "MongoClient":
        if self._client is None:
            self._client = self.generate_client()
        return self._client

    @requires_dependencies(["pymongo"], extras="mongodb")
    def check_connection(self):
        try:
            self.client.admin.command("ping")
        except Exception as e:
            logger.error(f"failed to validate connection: {e}", exc_info=True)
            raise DestinationConnectionError(f"failed to validate connection: {e}")

    def initialize(self):
        _ = self.client

    def conform_dict(self, data: dict) -> None:
        pass

    def get_collection(self):
        database = self.client[self.write_config.database]
        return database.get_collection(name=self.write_config.collection)

    @requires_dependencies(["pymongo"], extras="mongodb")
    def write_dict(self, *args, elements_dict: t.List[t.Dict[str, t.Any]], **kwargs) -> None:
        logger.info(
            f"writing {len(elements_dict)} documents to destination "
            f"database {self.write_config.database}, at collection {self.write_config.collection}",
        )

        collection = self.get_collection()
        try:
            collection.insert_many(elements_dict)
        except Exception as e:
            logger.error(f"failed to write records: {e}", exc_info=True)
            raise WriteError(f"failed to write records: {e}")

    def write(self, docs: t.List[BaseSingleIngestDoc]) -> None:
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
        self.write_dict(elements_dict=json_list)
