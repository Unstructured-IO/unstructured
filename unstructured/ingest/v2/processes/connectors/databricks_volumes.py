import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, Generator, Optional

from unstructured.documents.elements import DataSourceMetadata
from unstructured.ingest.enhanced_dataclass import enhanced_field
from unstructured.ingest.error import SourceConnectionNetworkError
from unstructured.ingest.v2.interfaces import (
    AccessConfig,
    ConnectionConfig,
    Downloader,
    DownloaderConfig,
    FileData,
    Indexer,
    IndexerConfig,
    SourceIdentifiers,
)
from unstructured.ingest.v2.logger import logger
from unstructured.ingest.v2.processes.connector_registry import (
    SourceRegistryEntry,
    add_source_entry,
)
from unstructured.utils import requires_dependencies

if TYPE_CHECKING:
    from databricks.sdk import WorkspaceClient

CONNECTOR_TYPE = "databricks_volumes"


@dataclass
class DatabricksVolumesAccessConfig(AccessConfig):
    password: Optional[str] = None
    client_secret: Optional[str] = None
    token: Optional[str] = (None,)


@dataclass
class DatabricksVolumesConnectionConfig(ConnectionConfig):
    host: Optional[str] = None
    account_id: Optional[str] = None
    username: Optional[str] = None
    client_id: Optional[str] = None
    access_config: DatabricksVolumesAccessConfig = enhanced_field(sensitive=True)

    @requires_dependencies(dependencies=["databricks.sdk"], extras="databricks")
    def get_client(self) -> "WorkspaceClient":
        from databricks.sdk import WorkspaceClient

        client_kwargs = self.to_dict()
        client_kwargs.pop("access_config", None)
        client_kwargs.update(self.access_config.to_dict())
        return WorkspaceClient(**client_kwargs)


@dataclass
class DatabricksVolumesIndexerConfig(IndexerConfig):
    remote_url: str
    recursive: bool = False
    catalog: str = field(init=False)
    path: str = field(init=False)
    full_name: str = field(init=False)

    def __post_init__(self):
        full_path = self.remote_url

        if full_path.startswith("/"):
            full_path = full_path[1:]
        parts = full_path.split("/")
        if parts[0] != "Volumes":
            raise ValueError(
                "remote url needs to be of the format /Volumes/catalog_name/volume/path"
            )
        self.catalog = parts[1]
        self.path = "/".join(parts[2:])
        self.full_name = ".".join(parts[1:])


@dataclass
class DatabricksVolumesIndexer(Indexer):
    connector_type: str = CONNECTOR_TYPE
    index_config: DatabricksVolumesIndexerConfig
    connection_config: DatabricksVolumesConnectionConfig
    workspace: "WorkspaceClient" = field(init=False)

    def __post_init__(self):
        self.workspace = self.connection_config.get_client()

    def run(self, **kwargs: Any) -> Generator[FileData, None, None]:
        for file_info in self.workspace.dbfs.list(
            path=self.index_config.remote_url, recursive=self.index_config.recursive
        ):
            if file_info.is_dir:
                continue
            rel_path = file_info.path.replace(self.index_config.remote_url, "")
            if rel_path.startswith("/"):
                rel_path = rel_path[1:]
            filename = Path(file_info.path).name
            yield FileData(
                identifier=file_info.path,
                connector_type=CONNECTOR_TYPE,
                source_identifiers=SourceIdentifiers(
                    filename=filename,
                    rel_path=rel_path,
                    fullpath=file_info.path,
                    additional_metadata={
                        "catalog": self.index_config.catalog,
                    },
                ),
                metadata=DataSourceMetadata(
                    url=file_info.path, date_modified=str(file_info.modification_time)
                ),
            )


@dataclass
class DatabricksVolumesDownloaderConfig(DownloaderConfig):
    pass


@dataclass
class DatabricksVolumesDownloader(Downloader):
    download_config: DatabricksVolumesDownloaderConfig
    connection_config: DatabricksVolumesConnectionConfig
    workspace: "WorkspaceClient" = field(init=False)

    def __post_init__(self):
        self.workspace = self.connection_config.get_client()

    def get_download_path(self, file_data: FileData) -> Path:
        return self.download_config.download_dir / Path(file_data.source_identifiers.relative_path)

    @staticmethod
    def is_float(value: str):
        try:
            float(value)
            return True
        except ValueError:
            return False

    def run(self, file_data: FileData, **kwargs: Any) -> Path:
        download_path = self.get_download_path(file_data=file_data)
        download_path.parent.mkdir(parents=True, exist_ok=True)
        logger.info(f"Writing {file_data.identifier} to {download_path}")
        try:
            with self.workspace.dbfs.download(path=file_data.identifier) as c:
                read_content = c._read_handle.read()
            with open(download_path, "wb") as f:
                f.write(read_content)

        except Exception as e:
            logger.error(f"failed to download file {file_data.identifier}: {e}", exc_info=True)
            raise SourceConnectionNetworkError(f"failed to download file {file_data.identifier}")
        if (
            file_data.metadata.date_modified
            and self.is_float(file_data.metadata.date_modified)
            and file_data.metadata.date_created
            and self.is_float(file_data.metadata.date_created)
        ):
            date_modified = float(file_data.metadata.date_modified)
            date_created = float(file_data.metadata.date_created)
            os.utime(download_path, times=(date_created, date_modified))
        return download_path


add_source_entry(
    source_type=CONNECTOR_TYPE,
    entry=SourceRegistryEntry(
        indexer=DatabricksVolumesIndexer,
        indexer_config=DatabricksVolumesIndexerConfig,
        downloader=DatabricksVolumesDownloader,
        downloader_config=DatabricksVolumesDownloaderConfig,
    ),
)
