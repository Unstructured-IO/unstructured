import json
import typing as t
from dataclasses import dataclass, field

from unstructured.ingest.error import DestinationConnectionError, SourceConnectionError
from unstructured.ingest.interfaces import (
    BaseConnectorConfig,
    BaseDestinationConnector,
    BaseIngestDoc,
    WriteConfig,
)
from unstructured.ingest.logger import logger
from unstructured.ingest.utils.conform import ConformDict
from unstructured.utils import requires_dependencies

if t.TYPE_CHECKING:
    from weaviate import Client


@dataclass
class SimpleWeaviateConfig(BaseConnectorConfig):
    host_url: str
    class_name: str
    auth_keys: t.Optional[t.Dict[str, str]] = None


@dataclass
class WeaviateWriteConfig(WriteConfig):
    batch_size: int = 100


@dataclass
class WeaviateDestinationConnector(BaseDestinationConnector):
    write_config: WeaviateWriteConfig
    connector_config: SimpleWeaviateConfig
    _client: t.Optional["Client"] = field(init=False, default=None)

    @property
    @requires_dependencies(["weaviate"], extras="weaviate")
    def client(self) -> "Client":
        if self._client is None:
            from weaviate import Client

            auth = self._resolve_auth_method()
            self._client = Client(url=self.connector_config.host_url, auth_client_secret=auth)
        return self._client

    @requires_dependencies(["weaviate"], extras="weaviate")
    @DestinationConnectionError.wrap
    def initialize(self):
        _ = self.client

    @requires_dependencies(["weaviate"], extras="weaviate")
    def check_connection(self):
        try:
            _ = self.client
        except Exception as e:
            logger.error(f"Failed to validate connection {e}", exc_info=True)
            raise SourceConnectionError(f"failed to validate connection: {e}")

    def _resolve_auth_method(self):
        if self.connector_config.auth_keys is None:
            return None

        if access_token := self.connector_config.auth_keys.get("access_token"):
            from weaviate.auth import AuthBearerToken

            return AuthBearerToken(
                access_token=access_token,
                refresh_token=self.connector_config.auth_keys.get("refresh_token"),
            )
        elif api_key := self.connector_config.auth_keys.get("api_key"):
            from weaviate.auth import AuthApiKey

            return AuthApiKey(api_key=api_key)
        elif client_secret := self.connector_config.auth_keys.get("client_secret"):
            from weaviate.auth import AuthClientCredentials

            return AuthClientCredentials(
                client_secret=client_secret, scope=self.connector_config.auth_keys.get("scope")
            )
        elif (username := self.connector_config.auth_keys.get("username")) and (
            pwd := self.connector_config.auth_keys.get("password")
        ):
            from weaviate.auth import AuthClientPassword

            return AuthClientPassword(
                username=username, password=pwd, scope=self.connector_config.auth_keys.get("scope")
            )
        return None

    def conform_dict(self, data: dict) -> None:
        """
        Updates the element dictionary to conform to the Weaviate schema
        """
        conform_instance = ConformDict()
        return conform_instance.conform(data)

    def write_dict(self, *args, json_list: t.List[t.Dict[str, t.Any]], **kwargs) -> None:
        logger.info(
            f"writing {len(json_list)} objects to destination "
            f"class {self.connector_config.class_name} "
            f"at {self.connector_config.host_url}",
        )
        self.client.batch.configure(batch_size=self.write_config.batch_size)
        with self.client.batch as b:
            for e in json_list:
                self.conform_dict(e)
                vector = e.pop("embeddings", None)
                b.add_data_object(
                    e,
                    self.connector_config.class_name,
                    vector=vector,
                )

    @requires_dependencies(["weaviate"], extras="weaviate")
    def write(self, docs: t.List[BaseIngestDoc]) -> None:
        json_list: t.List[t.Dict[str, t.Any]] = []
        for doc in docs:
            local_path = doc._output_filename
            with open(local_path) as json_file:
                json_content = json.load(json_file)
                logger.info(
                    f"appending {len(json_content)} json elements from content in {local_path}",
                )
                json_list.extend(json_content)
        self.write_dict(json_list=json_list)
