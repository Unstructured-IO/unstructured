import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional

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
    from couchbase.cluster import Cluster

CONNECTOR_TYPE = "couchbase"
SERVER_API_VERSION = "1"


@dataclass
class CouchbaseAccessConfig(AccessConfig):
    connection_string: str = enhanced_field(sensitive=True)
    username: str = enhanced_field(sensitive=True)
    password: str = enhanced_field(sensitive=True)


@dataclass
class CouchbaseConnectionConfig(ConnectionConfig):
    access_config: CouchbaseAccessConfig = enhanced_field(
        sensitive=True, default_factory=CouchbaseAccessConfig
    )
    bucket: Optional[str] = None
    scope: Optional[str] = None
    collection: Optional[str] = None
    batch_size: int = 50
    connector_type: str = CONNECTOR_TYPE


@dataclass
class CouchbaseUploadStagerConfig(UploadStagerConfig):
    pass


@dataclass
class CouchbaseUploadStager(UploadStager):
    upload_stager_config: CouchbaseUploadStagerConfig = field(
        default_factory=lambda: CouchbaseUploadStagerConfig()
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
class CouchbaseUploaderConfig(UploaderConfig):
    batch_size: int = 50


@dataclass
class CouchbaseUploader(Uploader):
    upload_config: CouchbaseUploaderConfig
    connection_config: CouchbaseConnectionConfig
    cluster: Optional["Cluster"] = field(init=False, default=None)
    connector_type: str = CONNECTOR_TYPE

    def __post_init__(self):
        self.cluster = self.connect_to_couchbase()

    @requires_dependencies(["couchbase"], extras="couchbase")
    def connect_to_couchbase(self) -> "Cluster":
        from datetime import timedelta

        from couchbase.auth import PasswordAuthenticator
        from couchbase.cluster import Cluster
        from couchbase.options import ClusterOptions

        connection_string = username = password = None
        access_conf = self.connection_config.access_config
        try:
            if access_conf.connection_string is not None:
                connection_string = access_conf.connection_string
            if access_conf.username is not None:
                username = access_conf.username
            if access_conf.password is not None:
                password = access_conf.password
        except Exception as e:
            raise f"please provide connection string, username and password : {e}"

        auth = PasswordAuthenticator(username, password)
        options = ClusterOptions(auth)
        options.apply_profile("wan_development")
        cluster = Cluster(connection_string, options)
        cluster.wait_until_ready(timedelta(seconds=5))
        return cluster

    def run(self, contents: list[UploadContent], **kwargs: Any) -> None:
        elements_dict = []
        for content in contents:
            with open(content.path) as elements_file:
                elements = json.load(elements_file)
                # Modify the elements to match the expected couchbase format
                for element in elements:
                    new_doc = {
                        element.pop("element_id", None): {
                            "embedding": element.pop("embeddings", None),
                            "text": element.pop("text", None),
                            "metadata": element.pop("metadata", None),
                            "type": element.pop("type", None),
                        }
                    }
                    elements_dict.append(new_doc)

        logger.info(
            f"writing {len(elements_dict)} objects to destination "
            f"bucket, {self.connection_config.bucket} "
            f"at {self.connection_config.access_config.connection_string}",
        )

        bucket = self.cluster.bucket(self.connection_config.bucket)
        scope = bucket.scope(self.connection_config.scope)
        collection = scope.collection(self.connection_config.collection)

        for chunk in batch_generator(elements_dict, self.upload_config.batch_size):
            collection.upsert_multi({doc_id: doc for doc in chunk for doc_id, doc in doc.items()})


couchbase_destination_entry = DestinationRegistryEntry(
    connection_config=CouchbaseConnectionConfig,
    uploader=CouchbaseUploader,
    uploader_config=CouchbaseUploaderConfig,
    upload_stager=CouchbaseUploadStager,
    upload_stager_config=CouchbaseUploadStagerConfig,
)
