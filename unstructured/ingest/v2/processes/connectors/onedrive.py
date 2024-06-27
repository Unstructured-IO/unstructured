import json
from dataclasses import dataclass, field
from pathlib import Path
from time import time
from typing import TYPE_CHECKING, Any, Generator, Optional

from dateutil import parser

from unstructured.documents.elements import DataSourceMetadata
from unstructured.ingest.enhanced_dataclass import enhanced_field
from unstructured.ingest.error import SourceConnectionError, SourceConnectionNetworkError
from unstructured.ingest.v2.interfaces import (
    AccessConfig,
    ConnectionConfig,
    Downloader,
    DownloaderConfig,
    DownloadResponse,
    FileData,
    Indexer,
    IndexerConfig,
    SourceIdentifiers,
    download_responses,
)
from unstructured.ingest.v2.logger import logger
from unstructured.ingest.v2.processes.connector_registry import (
    SourceRegistryEntry,
)
from unstructured.utils import requires_dependencies

if TYPE_CHECKING:
    from office365.graph_client import GraphClient
    from office365.onedrive.driveitems.driveItem import DriveItem

CONNECTOR_TYPE = "onedrive"
MAX_MB_SIZE = 512_000_000


@dataclass
class OnedriveAccessConfig(AccessConfig):
    client_cred: str


@dataclass
class OnedriveConnectionConfig(ConnectionConfig):
    client_id: str
    user_pname: str
    tenant: str = field(repr=False)
    authority_url: Optional[str] = field(repr=False, default="https://login.microsoftonline.com")
    access_config: OnedriveAccessConfig = enhanced_field(sensitive=True)

    @requires_dependencies(["msal"], extras="onedrive")
    def get_token(self):
        from msal import ConfidentialClientApplication

        try:
            app = ConfidentialClientApplication(
                authority=f"{self.authority_url}/{self.tenant}",
                client_id=self.client_id,
                client_credential=self.access_config.client_cred,
            )
            token = app.acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"])
        except ValueError as exc:
            logger.error("Couldn't set up credentials for OneDrive")
            raise exc
        if "error" in token:
            raise SourceConnectionNetworkError(
                "failed to fetch token, {}: {}".format(token["error"], token["error_description"])
            )
        return token

    @requires_dependencies(["office365"], extras="onedrive")
    def get_client(self) -> "GraphClient":
        from office365.graph_client import GraphClient

        client = GraphClient(self.get_token)
        return client


@dataclass
class OnedriveIndexerConfig(IndexerConfig):
    path: Optional[str] = field(default="")
    recursive: bool = False


@dataclass
class OnedriveIndexer(Indexer):
    connection_config: OnedriveConnectionConfig
    index_config: OnedriveIndexerConfig

    def list_objects(self, folder, recursive) -> list["DriveItem"]:
        drive_items = folder.children.get().execute_query()
        files = [d for d in drive_items if d.is_file]
        if not recursive:
            return files
        folders = [d for d in drive_items if d.is_folder]
        for f in folders:
            files.extend(self.list_objects(f, recursive))
        return files

    def get_root(self, client: "GraphClient") -> "DriveItem":
        root = client.users[self.connection_config.user_pname].drive.get().execute_query().root
        if fpath := self.index_config.path:
            root = root.get_by_path(fpath).get().execute_query()
            if root is None or not root.is_folder:
                raise ValueError(f"Unable to find directory, given: {fpath}")
        return root

    def get_properties(self, drive_item: "DriveItem") -> dict:
        properties = drive_item.properties
        filtered_properties = {}
        for k, v in properties.items():
            try:
                json.dumps(v)
                filtered_properties[k] = v
            except TypeError:
                pass
        return filtered_properties

    def drive_item_to_file_data(self, drive_item: "DriveItem") -> FileData:
        file_path = drive_item.parent_reference.path.split(":")[-1]
        file_path = file_path[1:] if file_path and file_path[0] == "/" else file_path
        filename = drive_item.name
        server_path = file_path + "/" + filename
        rel_path = server_path.replace(self.index_config.path, "").lstrip("/")
        date_modified_dt = (
            parser.parse(drive_item.last_modified_datetime)
            if drive_item.last_modified_datetime
            else None
        )
        date_created_at = (
            parser.parse(drive_item.created_datetime) if drive_item.created_datetime else None
        )
        return FileData(
            identifier=drive_item.id,
            connector_type=CONNECTOR_TYPE,
            source_identifiers=SourceIdentifiers(
                fullpath=server_path, filename=drive_item.name, rel_path=rel_path
            ),
            metadata=DataSourceMetadata(
                url=drive_item.parent_reference.path + "/" + drive_item.name,
                version=drive_item.etag,
                date_modified=str(date_modified_dt.timestamp()) if date_modified_dt else None,
                date_created=str(date_created_at.timestamp()) if date_modified_dt else None,
                date_processed=str(time()),
                record_locator={
                    "user_pname": self.connection_config.user_pname,
                    "server_relative_path": server_path,
                },
            ),
            additional_metadata=self.get_properties(drive_item=drive_item),
        )

    def run(self, **kwargs: Any) -> Generator[FileData, None, None]:
        client = self.connection_config.get_client()
        root = self.get_root(client=client)
        drive_items = self.list_objects(folder=root, recursive=self.index_config.recursive)
        for drive_item in drive_items:
            file_data = self.drive_item_to_file_data(drive_item=drive_item)
            yield file_data


@dataclass
class OnedriveDownloaderConfig(DownloaderConfig):
    pass


@dataclass
class OnedriveDownloader(Downloader):
    connection_config: OnedriveConnectionConfig
    download_config: OnedriveDownloaderConfig

    @SourceConnectionNetworkError.wrap
    def _fetch_file(self, file_data: FileData):
        if file_data.source_identifiers is None or not file_data.source_identifiers.fullpath:
            raise ValueError(
                f"file data doesn't have enough information to get "
                f"file content: {file_data.to_dict()}"
            )

        server_relative_path = file_data.source_identifiers.fullpath
        client = self.connection_config.get_client()
        root = client.users[self.connection_config.user_pname].drive.get().execute_query().root
        file = root.get_by_path(server_relative_path).get().execute_query()
        if not file:
            raise FileNotFoundError(f"file not found: {server_relative_path}")
        return file

    def get_download_path(self, file_data: FileData) -> Optional[Path]:
        rel_path = file_data.source_identifiers.relative_path
        rel_path = rel_path[1:] if rel_path.startswith("/") else rel_path
        return self.download_dir / Path(rel_path)

    @SourceConnectionError.wrap
    def run(self, file_data: FileData, **kwargs: Any) -> download_responses:
        file = self._fetch_file(file_data=file_data)
        fsize = file.get_property("size", 0)
        download_path = self.get_download_path(file_data=file_data)
        download_path.parent.mkdir(parents=True, exist_ok=True)
        logger.info(f"Downloading {file_data.source_identifiers.fullpath} to {download_path}")
        if fsize > MAX_MB_SIZE:
            logger.info(f"Downloading file with size: {fsize} bytes in chunks")
            with download_path.open(mode="wb") as f:
                file.download_session(f, chunk_size=1024 * 1024 * 100).execute_query()
        else:
            with download_path.open(mode="wb") as f:
                file.download(f).execute_query()
        return DownloadResponse(file_data=file_data, path=download_path)


onedrive_source_entry = SourceRegistryEntry(
    connection_config=OnedriveConnectionConfig,
    indexer_config=OnedriveIndexerConfig,
    indexer=OnedriveIndexer,
    downloader_config=OnedriveDownloaderConfig,
    downloader=OnedriveDownloader,
)
