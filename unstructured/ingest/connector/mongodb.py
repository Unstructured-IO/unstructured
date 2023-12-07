import json
import typing as t
from dataclasses import dataclass, field
from urllib.parse import unquote_plus

from dataclasses_json.core import Json

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


def parse_userinfo(userinfo: str) -> t.Tuple[str, str]:
    user, _, passwd = userinfo.partition(":")
    return unquote_plus(user), unquote_plus(passwd)


def redact(uri: str, redacted_text="***REDACTED***") -> str:
    """
    Cherry pick code from pymongo.uri_parser.parse_uri to only extract password and
    redact without needing to import pymongo library
    """

    SCHEME = "mongodb://"
    SRV_SCHEME = "mongodb+srv://"
    if uri.startswith(SCHEME):
        scheme_free = uri[len(SCHEME) :]  # noqa: E203
    elif uri.startswith(SRV_SCHEME):
        scheme_free = uri[len(SRV_SCHEME) :]  # noqa: E203
    else:
        raise ValueError(f"Invalid URI scheme: URI must begin with '{SCHEME}' or '{SRV_SCHEME}'")

    passwd = None

    host_part, _, path_part = scheme_free.partition("/")
    if not host_part:
        host_part = path_part
        path_part = ""

    if not path_part:
        # There was no slash in scheme_free, check for a sole "?".
        host_part, _, _ = host_part.partition("?")

    if "@" in host_part:
        userinfo, _, hosts = host_part.rpartition("@")
        _, passwd = parse_userinfo(userinfo)

    if passwd:
        uri = uri.replace(passwd, redacted_text)
    return uri


@dataclass
class SimpleMongoDBStorageConfig(BaseConnectorConfig):
    uri: t.Optional[str] = None
    host: t.Optional[str] = None
    port: int = 27017

    def to_dict(
        self, redact_sensitive=False, redacted_text="***REDACTED***", **kwargs
    ) -> t.Dict[str, Json]:
        d = super().to_dict(
            redact_sensitive=redact_sensitive, redacted_text=redacted_text, **kwargs
        )
        if redact_sensitive:
            if self.host:
                d["host"] = redact(uri=self.host, redacted_text=redacted_text)
            if self.uri:
                d["uri"] = redact(uri=self.uri, redacted_text=redacted_text)
        return d


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
                self.connector_config.uri, server_api=ServerApi(version=SERVER_API_VERSION)
            )
        else:
            return MongoClient(
                host=self.connector_config.host,
                port=self.connector_config.port,
                server_api=ServerApi(version=SERVER_API_VERSION),
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
