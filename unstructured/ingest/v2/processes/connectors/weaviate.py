import json
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional

from dateutil import parser

from unstructured.ingest.enhanced_dataclass import enhanced_field
from unstructured.ingest.v2.interfaces import (
    AccessConfig,
    ConnectionConfig,
    FileData,
    UploadContent,
    Uploader,
    UploaderConfig,
    UploadStager,
    UploadStagerConfig,
)
from unstructured.ingest.v2.logger import logger
from unstructured.ingest.v2.processes.connector_registry import (
    DestinationRegistryEntry,
    add_destination_entry,
)

if TYPE_CHECKING:
    from weaviate import Client

CONNECTOR_TYPE = "weaviate"


@dataclass
class WeaviateAccessConfig(AccessConfig):
    access_token: Optional[str]
    api_key: Optional[str]
    client_secret: Optional[str]
    password: Optional[str]


@dataclass
class WeaviateConnectionConfig(ConnectionConfig):
    host_url: str
    class_name: str
    access_config: WeaviateAccessConfig = enhanced_field(sensitive=True)
    username: Optional[str] = None
    anonymous: bool = False
    scope: Optional[list[str]] = None
    refresh_token: Optional[str] = None
    connector_type: str = CONNECTOR_TYPE


@dataclass
class WeaviateUploadStagerConfig(UploadStagerConfig):
    pass


@dataclass
class WeaviateUploadStager(UploadStager):
    upload_stager_config: WeaviateUploadStagerConfig = field(
        default_factory=lambda: WeaviateUploadStagerConfig()
    )

    @staticmethod
    def parse_date_string(date_string: str) -> date:
        try:
            timestamp = float(date_string)
            return datetime.fromtimestamp(timestamp)
        except Exception as e:
            logger.debug(f"date {date_string} string not a timestamp: {e}")
        return parser.parse(date_string)

    @classmethod
    def conform_dict(cls, data: dict) -> None:
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
            data["metadata"]["data_source"]["date_created"] = cls.parse_date_string(
                date_created
            ).strftime(
                "%Y-%m-%dT%H:%M:%S.%fZ",
            )

        if date_modified := data.get("metadata", {}).get("data_source", {}).get("date_modified"):
            data["metadata"]["data_source"]["date_modified"] = cls.parse_date_string(
                date_modified
            ).strftime(
                "%Y-%m-%dT%H:%M:%S.%fZ",
            )

        if date_processed := data.get("metadata", {}).get("data_source", {}).get("date_processed"):
            data["metadata"]["data_source"]["date_processed"] = cls.parse_date_string(
                date_processed
            ).strftime(
                "%Y-%m-%dT%H:%M:%S.%fZ",
            )

        if last_modified := data.get("metadata", {}).get("last_modified"):
            data["metadata"]["last_modified"] = cls.parse_date_string(last_modified).strftime(
                "%Y-%m-%dT%H:%M:%S.%fZ",
            )

        # String casting
        if version := data.get("metadata", {}).get("data_source", {}).get("version"):
            data["metadata"]["data_source"]["version"] = str(version)

        if page_number := data.get("metadata", {}).get("page_number"):
            data["metadata"]["page_number"] = str(page_number)

        if regex_metadata := data.get("metadata", {}).get("regex_metadata"):
            data["metadata"]["regex_metadata"] = str(json.dumps(regex_metadata))

    def run(
        self,
        elements_filepath: Path,
        file_data: FileData,
        output_dir: Path,
        output_filename: str,
        **kwargs: Any,
    ) -> Path:
        with open(elements_filepath) as elements_file:
            elements_contents = json.load(elements_file)
        for element in elements_contents:
            self.conform_dict(data=element)
        output_path = Path(output_dir) / Path(f"{output_filename}.json")
        with open(output_path, "w") as output_file:
            json.dump(elements_contents, output_file)
        return output_path


@dataclass
class WeaviateUploaderConfig(UploaderConfig):
    batch_size: int = 100


@dataclass
class WeaviateUploader(Uploader):
    upload_config: WeaviateUploaderConfig
    connection_config: WeaviateConnectionConfig
    client: Optional["Client"] = field(init=False)

    def __post_init__(self):
        from weaviate import Client

        auth = self._resolve_auth_method()
        self.client = Client(url=self.connection_config.host_url, auth_client_secret=auth)

    def is_async(self) -> bool:
        return True

    def _resolve_auth_method(self):
        access_configs = self.connection_config.access_config
        connection_config = self.connection_config
        if connection_config.anonymous:
            return None

        if access_configs.access_token:
            from weaviate.auth import AuthBearerToken

            return AuthBearerToken(
                access_token=access_configs.access_token,
                refresh_token=connection_config.refresh_token,
            )
        elif access_configs.api_key:
            from weaviate.auth import AuthApiKey

            return AuthApiKey(api_key=access_configs.api_key)
        elif access_configs.client_secret:
            from weaviate.auth import AuthClientCredentials

            return AuthClientCredentials(
                client_secret=access_configs.client_secret, scope=connection_config.scope
            )
        elif connection_config.username and access_configs.password:
            from weaviate.auth import AuthClientPassword

            return AuthClientPassword(
                username=connection_config.username,
                password=access_configs.password,
                scope=connection_config.scope,
            )
        return None

    def run(self, contents: list[UploadContent], **kwargs: Any) -> None:
        raise NotImplementedError

    async def run_async(self, path: Path, file_data: FileData, **kwargs: Any) -> None:
        with open(path) as elements_file:
            elements_dict = json.load(elements_file)

        logger.info(
            f"writing {len(elements_dict)} objects to destination "
            f"class {self.connection_config.class_name} "
            f"at {self.connection_config.host_url}",
        )

        self.client.batch.configure(batch_size=self.upload_config.batch_size)
        with self.client.batch as b:
            for e in elements_dict:
                vector = e.pop("embeddings", None)
                b.add_data_object(
                    e,
                    self.connection_config.class_name,
                    vector=vector,
                )


add_destination_entry(
    destination_type=CONNECTOR_TYPE,
    entry=DestinationRegistryEntry(
        connection_config=WeaviateConnectionConfig,
        uploader=WeaviateUploader,
        uploader_config=WeaviateUploaderConfig,
        upload_stager=WeaviateUploadStager,
        upload_stager_config=WeaviateUploadStagerConfig,
    ),
)
