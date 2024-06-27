from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

from unstructured.ingest.enhanced_dataclass import enhanced_field
from unstructured.ingest.v2.interfaces import (
    AccessConfig,
    ConnectionConfig,
    Uploader,
    UploaderConfig,
    UploadStager,
    UploadStagerConfig,
)
from unstructured.ingest.v2.processes.connector_registry import (
    DestinationRegistryEntry,
    add_destination_entry,
)

if TYPE_CHECKING:
    from singlestoredb.connection import Connection

CONNECTOR_TYPE = "singlestore"


@dataclass
class SingleStoreAccessConfig(AccessConfig):
    password: Optional[str] = None


@dataclass
class SingleStoreConnectionConfig(ConnectionConfig):
    host: Optional[str] = None
    port: Optional[int] = None
    user: Optional[str] = None
    database: Optional[str] = None
    access_config: SingleStoreAccessConfig = enhanced_field(sensitive=True)

    def get_connection(self) -> "Connection":
        import singlestoredb as s2

        conn = s2.connect(
            host=self.host,
            port=self.port,
            database=self.database,
            user=self.user,
            password=self.access_config.password,
        )
        return conn


@dataclass
class SingleStoreUploadStagerConfig(UploadStagerConfig):
    pass


@dataclass
class SingleStoreUploadStager(UploadStager):
    pass


@dataclass
class SingleStoreUploaderConfig(UploaderConfig):
    pass


@dataclass
class SingleStoreUploader(Uploader):
    connection_config: SingleStoreConnectionConfig
    upload_config: SingleStoreUploaderConfig


add_destination_entry(
    destination_type=CONNECTOR_TYPE,
    entry=DestinationRegistryEntry(
        connection_config=SingleStoreConnectionConfig,
        uploader=SingleStoreUploader,
        uploader_config=SingleStoreUploaderConfig,
        upload_stager=SingleStoreUploadStager,
        upload_stager_config=SingleStoreUploadStagerConfig,
    ),
)
