import json
import typing as t
from dataclasses import dataclass

from unstructured.ingest.error import DestinationConnectionError, SourceConnectionError
from unstructured.ingest.interfaces import (
    BaseConnectorConfig,
    BaseDestinationConnector,
    BaseIngestDoc,
    WriteConfig,
)
from unstructured.ingest.logger import logger
from unstructured.utils import requires_dependencies


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

    @requires_dependencies(["weaviate"], extras="weaviate")
    @DestinationConnectionError.wrap
    def initialize(self):
        from weaviate import Client

        auth = self._resolve_auth_method()
        self.client: Client = Client(url=self.connector_config.host_url, auth_client_secret=auth)

    @requires_dependencies(["weaviate"], extras="weaviate")
    def check_connection(self):
        from weaviate import Client

        try:
            auth = self._resolve_auth_method()
            _ = Client(url=self.connector_config.host_url, auth_client_secret=auth)
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
            data["metadata"]["data_source"]["date_created"] = date_created + "Z"

        if date_modified := data.get("metadata", {}).get("data_source", {}).get("date_modified"):
            data["metadata"]["data_source"]["date_modified"] = date_modified + "Z"

        if date_processed := data.get("metadata", {}).get("data_source", {}).get("date_processed"):
            data["metadata"]["data_source"]["date_processed"] = date_processed + "Z"

        if last_modified := data.get("metadata", {}).get("last_modified", {}):
            data["metadata"]["last_modified"] = last_modified + "Z"

        # String casting
        if version := data.get("metadata", {}).get("data_source", {}).get("version"):
            data["metadata"]["data_source"]["version"] = str(version)

        if page_number := data.get("metadata", {}).get("page_number"):
            data["metadata"]["page_number"] = str(page_number)

        if regex_metadata := data.get("metadata", {}).get("regex_metadata"):
            data["metadata"]["regex_metadata"] = str(json.dumps(regex_metadata))

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
                b.add_data_object(
                    {
                        "type": e.get("type", ""),
                        "element_id": e.get("element_id", ""),
                        "metadata": e.get("metadata", {}),
                        "text": e.get("text", ""),
                    },
                    self.connector_config.class_name,
                    vector=e.get("embeddings"),
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
