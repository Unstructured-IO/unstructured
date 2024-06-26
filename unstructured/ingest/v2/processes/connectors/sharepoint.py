import json
from dataclasses import dataclass, field
from pathlib import Path
from time import time
from typing import TYPE_CHECKING, Any, Generator, Optional

from dateutil import parser

from unstructured.documents.elements import DataSourceMetadata
from unstructured.ingest.enhanced_dataclass import enhanced_field
from unstructured.ingest.v2.interfaces import (
    AccessConfig,
    ConnectionConfig,
    Downloader,
    DownloaderConfig,
    FileData,
    Indexer,
    IndexerConfig,
    SourceIdentifiers,
    download_responses,
)
from unstructured.ingest.v2.logger import logger
from unstructured.ingest.v2.processes.connector_registry import (
    SourceRegistryEntry,
    add_source_entry,
)
from unstructured.utils import requires_dependencies

if TYPE_CHECKING:
    from office365.sharepoint.client_context import ClientContext
    from office365.sharepoint.files.file import File
    from office365.sharepoint.folders.folder import Folder
    from office365.sharepoint.publishing.pages.page import SitePage

CONNECTOR_TYPE = "sharepoint"

MAX_MB_SIZE = 512_000_000
CONTENT_LABELS = ["CanvasContent1", "LayoutWebpartsContent1", "TimeCreated"]


@dataclass
class SharepointAccessConfig(AccessConfig):
    client_cred: str


@dataclass
class SharepointConnectionConfig(ConnectionConfig):
    client_id: str
    site: str
    access_config: SharepointAccessConfig = enhanced_field(sensitive=True)

    @requires_dependencies(["office365"], extras="sharepoint")
    def get_client(self) -> "ClientContext":
        from office365.runtime.auth.client_credential import ClientCredential
        from office365.sharepoint.client_context import ClientContext

        try:
            credentials = ClientCredential(self.client_id, self.access_config.client_cred)
            site_client = ClientContext(self.site).with_credentials(credentials)
        except Exception as e:
            logger.error(f"Couldn't set Sharepoint client: {e}")
            raise e
        return site_client


@dataclass
class SharepointIndexerConfig(IndexerConfig):
    path: Optional[str] = None
    process_pages: bool = field(default=True, init=False)
    recursive: bool = False
    files_only: bool = False

    def __post_init__(self):
        self.process_pages = not self.files_only


@dataclass
class SharepointIndexer(Indexer):
    connection_config: SharepointConnectionConfig
    index_config: SharepointIndexerConfig

    def list_files(self, folder, recursive) -> list["File"]:
        if not recursive:
            folder.expand(["Files"]).get().execute_query()
            return folder.files

        folder.expand(["Files", "Folders"]).get().execute_query()
        files: list["File"] = folder.files
        folders: list["Folder"] = folder.folders
        for f in folders:
            if "/Forms" in f.serverRelativeUrl:
                continue
            files.extend(self.list_files(f, recursive))
        return files

    def get_properties(self, raw_properties: dict) -> dict:
        raw_properties = {k: v for k, v in raw_properties.items() if v}
        filtered_properties = {}
        for k, v in raw_properties.items():
            try:
                json.dumps(v)
                filtered_properties[k] = v
            except TypeError:
                pass
        return filtered_properties

    def list_pages(self, client: "ClientContext") -> list["SitePage"]:
        pages = client.site_pages.pages.get().execute_query()
        return pages

    def page_to_file_data(self, page: "SitePage") -> FileData:
        expansion_fields = [
            "FirstPublished",
            "Version",
            "AbsoluteUrl",
            "FileName",
            "LastModifiedBy",
            "UniqueId",
            "Modified",
        ]
        page.expand(expansion_fields).get().execute_query()
        version = page.properties.get("Version", None)
        unique_id = page.properties.get("UniqueId", None)
        modified_date = page.properties.get("Modified", None)
        url = page.properties.get("AbsoluteUrl", None)
        date_modified_dt = parser.parse(modified_date) if modified_date else None
        date_created_at = (
            parser.parse(page.first_published)
            if (page.first_published and page.first_published != "0001-01-01T08:00:00Z")
            else None
        )
        file_path = page.get_property("Url", "")
        server_path = file_path if file_path[0] != "/" else file_path[1:]
        return FileData(
            identifier=unique_id,
            connector_type=CONNECTOR_TYPE,
            source_identifiers=SourceIdentifiers(
                filename=page.file_name,
                fullpath=file_path,
                rel_path=file_path.replace(self.index_config.path, ""),
            ),
            metadata=DataSourceMetadata(
                url=url,
                version=version,
                date_modified=str(date_modified_dt.timestamp()) if date_modified_dt else None,
                date_created=str(date_created_at.timestamp()) if date_created_at else None,
                date_processed=str(time()),
                record_locator={
                    "server_path": server_path,
                },
            ),
            additional_metadata=self.get_properties(raw_properties=page.properties),
        )

    def file_to_file_data(self, file: "File") -> FileData:
        expansion_fields = [
            "Name",
            "TimeCreated",
            "MinorVersion",
            "MajorVersion",
            "UniqueId",
            "Length",
            "ServerRelativePath",
            "ServerRelativeUrl",
            "TimeLastModified",
        ]
        file.expand(expansion_fields).get().execute_query()
        linking_url = file.properties.get("LinkingUrl", None)
        absolute_url = None
        if linking_url:
            absolute_url = linking_url.split("?")[0]
        date_modified_dt = (
            parser.parse(file.time_last_modified) if file.time_last_modified else None
        )
        date_created_at = parser.parse(file.time_created) if file.time_created else None
        return FileData(
            identifier=file.unique_id,
            connector_type=CONNECTOR_TYPE,
            source_identifiers=SourceIdentifiers(
                filename=file.name,
                fullpath=str(file.server_relative_path),
                rel_path=str(file.server_relative_path).replace(self.index_config.path, ""),
            ),
            metadata=DataSourceMetadata(
                url=absolute_url or file.serverRelativeUrl,
                version=f"{file.major_version}.{file.minor_version}",
                date_modified=str(date_modified_dt.timestamp()) if date_modified_dt else None,
                date_created=str(date_created_at.timestamp()) if date_created_at else None,
                date_processed=str(time()),
                record_locator={
                    "server_path": file.serverRelativeUrl,
                },
            ),
            additional_metadata=self.get_properties(raw_properties=file.properties),
        )

    def get_root(self, client: "ClientContext") -> "Folder":
        if path := self.index_config.path:
            return client.web.get_folder_by_server_relative_path(path)
        return client.web.root_folder

    def run(self, **kwargs: Any) -> Generator[FileData, None, None]:
        client = self.connection_config.get_client()
        root_folder = self.get_root(client=client)
        files = self.list_files(root_folder, recursive=self.index_config.recursive)
        for file in files:
            file_data = self.file_to_file_data(file=file)
            file_data.metadata.record_locator["site_url"] = client.base_url
            yield file_data
        if self.index_config.process_pages:
            pages = self.list_pages(client=client)
            for page in pages:
                file_data = self.page_to_file_data(page=page)
                file_data.metadata.record_locator["site_url"] = client.base_url
                yield file_data


@dataclass
class SharepointDownloaderConfig(DownloaderConfig):
    pass


@dataclass
class SharepointDownloader(Downloader):
    connection_config: SharepointConnectionConfig
    download_config: SharepointDownloaderConfig

    def get_download_path(self, file_data: FileData) -> Optional[Path]:
        return None

    def run(self, file_data: FileData, **kwargs: Any) -> download_responses:
        pass


add_source_entry(
    source_type=CONNECTOR_TYPE,
    entry=SourceRegistryEntry(
        connection_config=SharepointConnectionConfig,
        indexer_config=SharepointIndexerConfig,
        indexer=SharepointIndexer,
        downloader_config=SharepointDownloaderConfig,
        downloader=SharepointDownloader,
    ),
)
