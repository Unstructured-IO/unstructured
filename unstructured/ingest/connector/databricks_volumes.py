import copy
import json
import os
import typing as t
from dataclasses import dataclass, field
from io import BytesIO
from pathlib import PurePath

from unstructured.ingest.enhanced_dataclass import enhanced_field
from unstructured.ingest.enhanced_dataclass.core import _asdict
from unstructured.ingest.error import DestinationConnectionError
from unstructured.ingest.interfaces import (
    AccessConfig,
    BaseConnectorConfig,
    BaseDestinationConnector,
    BaseSingleIngestDoc,
    WriteConfig,
)
from unstructured.ingest.logger import logger
from unstructured.utils import requires_dependencies

if t.TYPE_CHECKING:
    from databricks.sdk import WorkspaceClient


@dataclass
class DatabricksVolumesAccessConfig(AccessConfig):
    account_id: t.Optional[str] = None
    username: t.Optional[str] = None
    password: t.Optional[str] = enhanced_field(default=None, sensitive=True)
    client_id: t.Optional[str] = None
    client_secret: t.Optional[str] = enhanced_field(default=None, sensitive=True)
    token: t.Optional[str] = enhanced_field(default=None, sensitive=True)
    profile: t.Optional[str] = None
    azure_workspace_resource_id: t.Optional[str] = None
    azure_client_secret: t.Optional[str] = enhanced_field(default=None, sensitive=True)
    azure_client_id: t.Optional[str] = None
    azure_tenant_id: t.Optional[str] = None
    azure_environment: t.Optional[str] = None
    auth_type: t.Optional[str] = None
    cluster_id: t.Optional[str] = None
    google_credentials: t.Optional[str] = None
    google_service_account: t.Optional[str] = None


@dataclass
class SimpleDatabricksVolumesConfig(BaseConnectorConfig):
    access_config: DatabricksVolumesAccessConfig
    host: t.Optional[str] = None


@dataclass
class DatabricksVolumesWriteConfig(WriteConfig):
    volume: str
    catalog: str
    volume_path: t.Optional[str] = None
    overwrite: bool = False
    encoding: str = "utf-8"
    schema: str = "default"

    @property
    def path(self) -> str:
        path = f"/Volumes/{self.catalog}/{self.schema}/{self.volume}"
        if self.volume_path:
            path = f"{path}/{self.volume_path}"
        return path


@dataclass
class DatabricksVolumesDestinationConnector(BaseDestinationConnector):
    write_config: DatabricksVolumesWriteConfig
    connector_config: SimpleDatabricksVolumesConfig
    _client: t.Optional["WorkspaceClient"] = field(init=False, default=None)

    def to_dict(self, **kwargs):
        self_cp = copy.copy(self)
        if hasattr(self_cp, "_client"):
            setattr(self_cp, "_client", None)
        return _asdict(self_cp, **kwargs)

    @requires_dependencies(dependencies=["databricks.sdk"], extras="databricks-volumes")
    def generate_client(self) -> "WorkspaceClient":
        from databricks.sdk import WorkspaceClient

        return WorkspaceClient(
            host=self.connector_config.host, **self.connector_config.access_config.to_dict()
        )

    @property
    def client(self) -> "WorkspaceClient":
        if self._client is None:
            self._client = self.generate_client()
        return self._client

    def check_connection(self):
        try:
            assert self.client.current_user.me().active
        except Exception as e:
            logger.error(f"failed to validate connection: {e}", exc_info=True)
            raise DestinationConnectionError(f"failed to validate connection: {e}")

    def initialize(self):
        _ = self.client

    def write_dict(
        self,
        *args,
        elements_dict: t.List[t.Dict[str, t.Any]],
        filename: t.Optional[str] = None,
        indent: int = 4,
        encoding: str = "utf-8",
        **kwargs,
    ) -> None:
        output_folder = self.write_config.path
        output_folder = os.path.join(output_folder)  # Make sure folder ends with file seperator
        filename = (
            filename.strip(os.sep) if filename else filename
        )  # Make sure filename doesn't begin with file seperator
        output_path = str(PurePath(output_folder, filename)) if filename else output_folder
        logger.debug(f"uploading content to {output_path}")
        self.client.files.upload(
            file_path=output_path,
            contents=BytesIO(json.dumps(elements_dict).encode(encoding=self.write_config.encoding)),
            overwrite=self.write_config.overwrite,
        )

    def get_elements_dict(self, docs: t.List[BaseSingleIngestDoc]) -> t.List[t.Dict[str, t.Any]]:
        pass

    def write(self, docs: t.List[BaseSingleIngestDoc]) -> None:
        for doc in docs:
            file_path = doc.base_output_filename
            filename = file_path if file_path else None
            with open(doc._output_filename) as json_file:
                logger.debug(f"uploading content from {doc._output_filename}")
                json_list = json.load(json_file)
                self.write_dict(elements_dict=json_list, filename=filename)
