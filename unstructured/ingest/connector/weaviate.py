import copy
import json
import typing as t
from dataclasses import dataclass, field

from unstructured.ingest.enhanced_dataclass import enhanced_field
from unstructured.ingest.enhanced_dataclass.core import _asdict
from unstructured.ingest.error import DestinationConnectionError, SourceConnectionError
from unstructured.ingest.interfaces import (
    AccessConfig,
    BaseConnectorConfig,
    BaseDestinationConnector,
    WriteConfig,
)
from unstructured.ingest.logger import logger
from unstructured.utils import requires_dependencies

if t.TYPE_CHECKING:
    from weaviate import Client


@dataclass
class WeaviateAccessConfig(AccessConfig):
    access_token: t.Optional[str] = enhanced_field(default=None, sensitive=True)
    refresh_token: t.Optional[str] = enhanced_field(default=None, sensitive=True)
    api_key: t.Optional[str] = enhanced_field(default=None, sensitive=True)
    client_secret: t.Optional[str] = enhanced_field(default=None, sensitive=True)
    scope: t.Optional[t.List[str]] = None
    username: t.Optional[str] = None
    password: t.Optional[str] = enhanced_field(default=None, sensitive=True)
    anonymous: bool = False


@dataclass
class SimpleWeaviateConfig(BaseConnectorConfig):
    access_config: WeaviateAccessConfig
    host_url: str
    class_name: str


@dataclass
class WeaviateWriteConfig(WriteConfig):
    batch_size: int = 100


@dataclass
class WeaviateDestinationConnector(BaseDestinationConnector):
    write_config: WeaviateWriteConfig
    connector_config: SimpleWeaviateConfig
    _client: t.Optional["Client"] = field(init=False, default=None)

    def to_dict(self, **kwargs):
        """
        The _client variable in this dataclass breaks deepcopy due to:
        TypeError: cannot pickle '_thread.lock' object
        When serializing, remove it, meaning client data will need to be reinitialized
        when deserialized
        """
        self_cp = copy.copy(self)
        if hasattr(self_cp, "_client"):
            setattr(self_cp, "_client", None)
        return _asdict(self_cp, **kwargs)

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
        access_configs = self.connector_config.access_config
        if access_configs.anonymous:
            return None

        if access_configs.access_token:
            from weaviate.auth import AuthBearerToken

            return AuthBearerToken(
                access_token=access_configs.access_token,
                refresh_token=access_configs.refresh_token,
            )
        elif access_configs.api_key:
            from weaviate.auth import AuthApiKey

            return AuthApiKey(api_key=access_configs.api_key)
        elif access_configs.client_secret:
            from weaviate.auth import AuthClientCredentials

            return AuthClientCredentials(
                client_secret=access_configs.client_secret, scope=access_configs.scope
            )
        elif access_configs.username and access_configs.password:
            from weaviate.auth import AuthClientPassword

            return AuthClientPassword(
                username=access_configs.username,
                password=access_configs.password,
                scope=access_configs.scope,
            )
        return None

    def conform_dict(self, data: dict) -> None:
        """
        Updates the element dictionary to conform to the Weaviate schema
        """
        from dateutil import parser

        # Dict as string formatting
        if record_locator := data.get("metadata", {}).get("data_source", {}).get("record_locator"):
            # Explicit casting otherwise fails schema type checking
            data["metadata"]["data_source"]["record_locator"] = str(json.dumps(record_locator))

        # Array of items as string formatting
        if points := data.get("metadata", {}).get("coordinates", {}).get("points"):
            data["metadata"]["coordinates"]["points"] = str(json.dumps(points))

        if links := data.get("metadata", {}).get("links", {}):
            data["metadata"]["links"] = str(json.dumps(links))

        if permissions_data := (
            data.get("metadata", {}).get("data_source", {}).get("permissions_data")
        ):
            data["metadata"]["data_source"]["permissions_data"] = json.dumps(permissions_data)

        # Datetime formatting
        if date_created := data.get("metadata", {}).get("data_source", {}).get("date_created"):
            data["metadata"]["data_source"]["date_created"] = parser.parse(date_created).strftime(
                "%Y-%m-%dT%H:%M:%S.%fZ",
            )

        if date_modified := data.get("metadata", {}).get("data_source", {}).get("date_modified"):
            data["metadata"]["data_source"]["date_modified"] = parser.parse(date_modified).strftime(
                "%Y-%m-%dT%H:%M:%S.%fZ",
            )

        if date_processed := data.get("metadata", {}).get("data_source", {}).get("date_processed"):
            data["metadata"]["data_source"]["date_processed"] = parser.parse(
                date_processed
            ).strftime(
                "%Y-%m-%dT%H:%M:%S.%fZ",
            )

        if last_modified := data.get("metadata", {}).get("last_modified", {}):
            data["metadata"]["last_modified"] = parser.parse(last_modified).strftime(
                "%Y-%m-%dT%H:%M:%S.%fZ",
            )

        # String casting
        if version := data.get("metadata", {}).get("data_source", {}).get("version"):
            data["metadata"]["data_source"]["version"] = str(version)

        if page_number := data.get("metadata", {}).get("page_number"):
            data["metadata"]["page_number"] = str(page_number)

        if regex_metadata := data.get("metadata", {}).get("regex_metadata"):
            data["metadata"]["regex_metadata"] = str(json.dumps(regex_metadata))

    def write_dict(self, *args, elements_dict: t.List[t.Dict[str, t.Any]], **kwargs) -> None:
        logger.info(
            f"writing {len(elements_dict)} objects to destination "
            f"class {self.connector_config.class_name} "
            f"at {self.connector_config.host_url}",
        )

        self.client.batch.configure(batch_size=self.write_config.batch_size)
        with self.client.batch as b:
            for e in elements_dict:
                vector = e.pop("embeddings", None)
                b.add_data_object(
                    e,
                    self.connector_config.class_name,
                    vector=vector,
                )
