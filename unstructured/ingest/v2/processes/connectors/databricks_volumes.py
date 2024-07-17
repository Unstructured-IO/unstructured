import os
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Optional

from unstructured.ingest.enhanced_dataclass import enhanced_field
from unstructured.ingest.v2.interfaces import (
    AccessConfig,
    ConnectionConfig,
    UploadContent,
    Uploader,
    UploaderConfig,
)
from unstructured.ingest.v2.processes.connector_registry import DestinationRegistryEntry
from unstructured.utils import requires_dependencies

if TYPE_CHECKING:
    from databricks.sdk import WorkspaceClient

CONNECTOR_TYPE = "databricks_volumes"


@dataclass
class DatabricksVolumesAccessConfig(AccessConfig):
    account_id: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    token: Optional[str] = None
    profile: Optional[str] = None
    azure_workspace_resource_id: Optional[str] = None
    azure_client_secret: Optional[str] = None
    azure_client_id: Optional[str] = None
    azure_tenant_id: Optional[str] = None
    azure_environment: Optional[str] = None
    auth_type: Optional[str] = None
    cluster_id: Optional[str] = None
    google_credentials: Optional[str] = None
    google_service_account: Optional[str] = None


@dataclass
class DatabricksVolumesConnectionConfig(ConnectionConfig):
    access_config: DatabricksVolumesAccessConfig = enhanced_field(
        default_factory=DatabricksVolumesAccessConfig, sensitive=True
    )
    host: Optional[str] = None


@dataclass
class DatabricksVolumesUploaderConfig(UploaderConfig):
    volume: str
    catalog: str
    volume_path: Optional[str] = None
    overwrite: bool = False
    schema: str = "default"

    @property
    def path(self) -> str:
        path = f"/Volumes/{self.catalog}/{self.schema}/{self.volume}"
        if self.volume_path:
            path = f"{path}/{self.volume_path}"
        return path


@dataclass
class DatabricksVolumesUploader(Uploader):
    connector_type: str = CONNECTOR_TYPE
    upload_config: DatabricksVolumesUploaderConfig
    connection_config: DatabricksVolumesConnectionConfig
    client: Optional["WorkspaceClient"] = field(init=False, default=None)

    @requires_dependencies(dependencies=["databricks.sdk"], extras="databricks-volumes")
    def __post_init__(self) -> "WorkspaceClient":
        from databricks.sdk import WorkspaceClient

        self.client = WorkspaceClient(
            host=self.connection_config.host, **self.connection_config.access_config.to_dict()
        )

    def run(self, contents: list[UploadContent], **kwargs: Any) -> None:
        for content in contents:
            with open(content.path, "rb") as elements_file:
                output_path = os.path.join(self.upload_config.path, content.path.name)
                self.client.files.upload(
                    file_path=output_path,
                    contents=elements_file,
                    overwrite=self.upload_config.overwrite,
                )


databricks_volumes_destination_entry = DestinationRegistryEntry(
    connection_config=DatabricksVolumesConnectionConfig,
    uploader=DatabricksVolumesUploader,
    uploader_config=DatabricksVolumesUploaderConfig,
)
