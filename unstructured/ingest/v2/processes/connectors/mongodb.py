import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional

from unstructured.__version__ import __version__ as unstructured_version
from unstructured.ingest.enhanced_dataclass import enhanced_field
from unstructured.ingest.utils.data_prep import batch_generator
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
)
from unstructured.utils import requires_dependencies

if TYPE_CHECKING:
    from pymongo import MongoClient

CONNECTOR_TYPE = "mongodb"
SERVER_API_VERSION = "1"


@dataclass
class MongoDBAccessConfig(AccessConfig):
    uri: Optional[str] = None


@dataclass
class MongoDBConnectionConfig(ConnectionConfig):
    access_config: MongoDBAccessConfig = enhanced_field(
        sensitive=True, default_factory=MongoDBAccessConfig
    )
    host: Optional[str] = None
    database: Optional[str] = None
    collection: Optional[str] = None
    port: int = 27017
    batch_size: int = 100
    connector_type: str = CONNECTOR_TYPE


@dataclass
class MongoDBUploadStagerConfig(UploadStagerConfig):
    pass


@dataclass
class MongoDBUploadStager(UploadStager):
    upload_stager_config: MongoDBUploadStagerConfig = field(
        default_factory=lambda: MongoDBUploadStagerConfig()
    )

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

        output_path = Path(output_dir) / Path(f"{output_filename}.json")
        with open(output_path, "w") as output_file:
            json.dump(elements_contents, output_file)
        return output_path


@dataclass
class MongoDBUploaderConfig(UploaderConfig):
    batch_size: int = 100


@dataclass
class MongoDBUploader(Uploader):
    upload_config: MongoDBUploaderConfig
    connection_config: MongoDBConnectionConfig
    client: Optional["MongoClient"] = field(init=False)
    connector_type: str = CONNECTOR_TYPE

    def __post_init__(self):
        self.client = self.create_client()

    @requires_dependencies(["pymongo"], extras="mongodb")
    def create_client(self) -> "MongoClient":
        from pymongo import MongoClient
        from pymongo.driver_info import DriverInfo
        from pymongo.server_api import ServerApi

        if self.connection_config.access_config.uri:
            return MongoClient(
                self.connection_config.access_config.uri,
                server_api=ServerApi(version=SERVER_API_VERSION),
                driver=DriverInfo(name="unstructured", version=unstructured_version),
            )
        else:
            return MongoClient(
                host=self.connection_config.host,
                port=self.connection_config.port,
                server_api=ServerApi(version=SERVER_API_VERSION),
            )

    def run(self, contents: list[UploadContent], **kwargs: Any) -> None:
        elements_dict = []
        for content in contents:
            with open(content.path) as elements_file:
                elements = json.load(elements_file)
                elements_dict.extend(elements)

        logger.info(
            f"writing {len(elements_dict)} objects to destination "
            f"db, {self.connection_config.database}, "
            f"collection {self.connection_config.collection} "
            f"at {self.connection_config.host}",
        )
        db = self.client[self.connection_config.database]
        collection = db[self.connection_config.collection]
        for chunk in batch_generator(elements_dict, self.upload_config.batch_size):
            collection.insert_many(chunk)


mongodb_destination_entry = DestinationRegistryEntry(
    connection_config=MongoDBConnectionConfig,
    uploader=MongoDBUploader,
    uploader_config=MongoDBUploaderConfig,
    upload_stager=MongoDBUploadStager,
    upload_stager_config=MongoDBUploadStagerConfig,
)
