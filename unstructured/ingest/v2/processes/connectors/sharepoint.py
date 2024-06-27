import json
from dataclasses import dataclass, field
from pathlib import Path
from time import time
from typing import TYPE_CHECKING, Any, Generator, Optional
from urllib.parse import quote

from dateutil import parser

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
    download_responses,
)
from unstructured.ingest.v2.logger import logger
from unstructured.ingest.v2.processes.connector_registry import (
    SourceRegistryEntry,
    add_source_entry,
)
from unstructured.utils import requires_dependencies

if TYPE_CHECKING:
    from office365.graph_client import GraphClient
    from office365.onedrive.driveitems.driveItem import DriveItem
    from office365.onedrive.drives.drive import Drive
    from office365.onedrive.permissions.permission import Permission
    from office365.onedrive.sites.site import Site
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
class SharepointPermissionsConfig:
    permissions_application_id: str
    permissions_tenant: str
    permissions_client_cred: str = enhanced_field(sensitive=True)
    authority_url: Optional[str] = field(repr=False, default="https://login.microsoftonline.com")


@dataclass
class SharepointConnectionConfig(ConnectionConfig):
    client_id: str
    site: str
    access_config: SharepointAccessConfig = enhanced_field(sensitive=True)
    permissions_config: Optional[SharepointPermissionsConfig] = None

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

    @requires_dependencies(["msal"], extras="sharepoint")
    def get_permissions_token(self):
        from msal import ConfidentialClientApplication

        try:
            app = ConfidentialClientApplication(
                authority=f"{self.permissions_config.authority_url}/"
                f"{self.permissions_config.permissions_tenant}",
                client_id=self.permissions_config.permissions_application_id,
                client_credential=self.permissions_config.permissions_client_cred,
            )
            token = app.acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"])
        except ValueError as exc:
            logger.error("Couldn't set up credentials for Sharepoint")
            raise exc
        if "error" in token:
            raise SourceConnectionNetworkError(
                "failed to fetch token, {}: {}".format(token["error"], token["error_description"])
            )
        return token

    @requires_dependencies(["office365"], extras="sharepoint")
    def get_permissions_client(self) -> Optional["GraphClient"]:
        from office365.graph_client import GraphClient

        if self.permissions_config is None:
            return None

        client = GraphClient(self.get_permissions_token)
        return client


@dataclass
class SharepointIndexerConfig(IndexerConfig):
    path: Optional[str] = None
    process_pages: bool = field(default=True, init=False)
    recursive: bool = False
    omit_files: bool = False
    omit_pages: bool = False
    omit_lists: bool = False


@dataclass
class SharepointIndexer(Indexer):
    connection_config: SharepointConnectionConfig
    index_config: SharepointIndexerConfig

    def list_files(self, folder: "Folder", recursive: bool = False) -> list["File"]:
        if not recursive:
            folder.expand(["Files"]).get().execute_query()
            return folder.files

        folder.expand(["Files", "Folders"]).get().execute_query()
        files: list["File"] = list(folder.files)
        folders: list["Folder"] = list(folder.folders)
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

    def file_to_file_data(self, client: "ClientContext", file: "File") -> FileData:
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
        absolute_url = f"{client.base_url}{quote(file.serverRelativeUrl)}"
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
                url=absolute_url,
                version=f"{file.major_version}.{file.minor_version}",
                date_modified=str(date_modified_dt.timestamp()) if date_modified_dt else None,
                date_created=str(date_created_at.timestamp()) if date_created_at else None,
                date_processed=str(time()),
                record_locator={"server_path": file.serverRelativeUrl, "site_url": client.base_url},
            ),
            additional_metadata=self.get_properties(raw_properties=file.properties),
        )

    def get_root(self, client: "ClientContext") -> "Folder":
        if path := self.index_config.path:
            return client.web.get_folder_by_server_relative_path(path)
        default_document_library = client.web.default_document_library()
        root_folder = default_document_library.root_folder
        root_folder = root_folder.get().execute_query()
        self.index_config.path = root_folder.name
        return root_folder

    def get_site_url(self, client: "ClientContext") -> str:
        res = client.web.get().execute_query()
        return res.url

    def get_site(self, permissions_client: "GraphClient", site_url) -> "Site":
        return permissions_client.sites.get_by_url(url=site_url).execute_query()

    def get_permissions_items(self, site: "Site") -> list["DriveItem"]:
        # TODO find a way to narrow this search down by name of drive
        items: list["DriveItem"] = []
        drives: list["Drive"] = site.drives.get_all().execute_query()
        for drive in drives:
            items.extend(drive.root.children.get_all().execute_query())
        return items

    def map_permission(self, permission: "Permission") -> dict:
        return {
            "id": permission.id,
            "roles": list(permission.roles),
            "share_id": permission.share_id,
            "has_password": permission.has_password,
            "link": permission.link.to_json(),
            "granted_to_identities": permission.granted_to_identities.to_json(),
            "granted_to": permission.granted_to.to_json(),
            "granted_to_v2": permission.granted_to_v2.to_json(),
            "granted_to_identities_v2": permission.granted_to_identities_v2.to_json(),
            "invitation": permission.invitation.to_json(),
        }

    def enrich_permissions_on_files(self, all_file_data: list[FileData], site_url: str) -> None:
        logger.debug("Enriching permissions on files")
        permission_client = self.connection_config.get_permissions_client()
        if permission_client is None:
            return
        site = self.get_site(permissions_client=permission_client, site_url=site_url)
        existing_items = self.get_permissions_items(site=site)
        for file_data in all_file_data:
            etag = file_data.additional_metadata.get("ETag")
            if not etag:
                continue
            matching_items = list(filter(lambda x: x.etag == etag, existing_items))
            if not matching_items:
                continue
            if len(matching_items) > 1:
                logger.warning(
                    "Found multiple drive items with etag matching {}, skipping: {}".format(
                        etag, ", ".join([i.name for i in matching_items])
                    )
                )
                continue
            matching_item = matching_items[0]
            permissions: list["Permission"] = matching_item.permissions.get_all().execute_query()
            permissions_data = [
                self.map_permission(permission=permission) for permission in permissions
            ]
            file_data.metadata.permissions_data = permissions_data

    def run(self, **kwargs: Any) -> Generator[FileData, None, None]:
        client = self.connection_config.get_client()
        root_folder = self.get_root(client=client)
        if not self.index_config.omit_files:
            files = self.list_files(root_folder, recursive=self.index_config.recursive)
            file_data = [self.file_to_file_data(file=file, client=client) for file in files]
            self.enrich_permissions_on_files(
                all_file_data=file_data, site_url=self.get_site_url(client=client)
            )
            for file in file_data:
                yield file
        if not self.index_config.omit_pages:
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

    def get_download_path(self, file_data: FileData) -> Path:
        rel_path = file_data.source_identifiers.relative_path
        rel_path = rel_path[1:] if rel_path.startswith("/") else rel_path
        return self.download_dir / Path(rel_path)

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
