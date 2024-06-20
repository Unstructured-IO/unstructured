from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Generator, Optional

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

CONNECTOR_TYPE = "onedrive"
MAX_MB_SIZE = 512_000_000


@dataclass
class OnedriveAccessConfig(AccessConfig):
    client_credential: str


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
                client_credential=self.access_config.client_credential,
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
    indexer_config: OnedriveIndexerConfig

    def run(self, **kwargs: Any) -> Generator[FileData, None, None]:
        pass


@dataclass
class OnedriveDownloaderConfig(DownloaderConfig):
    pass


@dataclass
class OnedriveDownloader(Downloader):
    connection_config: OnedriveConnectionConfig
    downloader_config: OnedriveDownloaderConfig

    def run(self, file_data: FileData, **kwargs: Any) -> download_responses:
        pass


add_source_entry(
    source_type=CONNECTOR_TYPE,
    entry=SourceRegistryEntry(
        connection_config=OnedriveConnectionConfig,
        indexer_config=OnedriveIndexerConfig,
        indexer=OnedriveIndexer,
        downloader_config=OnedriveDownloaderConfig,
        downloader=OnedriveDownloader,
    ),
)
