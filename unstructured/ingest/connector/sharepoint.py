import typing as t
from dataclasses import dataclass, field
from datetime import datetime
from html import unescape
from pathlib import Path
from urllib.parse import urlparse

from unstructured.documents.elements import Element
from unstructured.embed.interfaces import BaseEmbeddingEncoder
from unstructured.file_utils.filetype import EXT_TO_FILETYPE
from unstructured.ingest.error import SourceConnectionError
from unstructured.ingest.interfaces import (
    BaseConnectorConfig,
    BaseIngestDoc,
    BaseSourceConnector,
    ChunkingConfig,
    EmbeddingConfig,
    IngestDocCleanupMixin,
    SourceConnectorCleanupMixin,
    SourceMetadata,
)
from unstructured.ingest.logger import logger
from unstructured.utils import requires_dependencies

if t.TYPE_CHECKING:
    from office365.sharepoint.client_context import ClientContext
    from office365.sharepoint.files.file import File
    from office365.sharepoint.publishing.pages.page import SitePage

MAX_MB_SIZE = 512_000_000
CONTENT_LABELS = ["CanvasContent1", "LayoutWebpartsContent1", "TimeCreated"]


@dataclass
class SimpleSharepointConfig(BaseConnectorConfig):
    client_id: str
    client_credential: str = field(repr=False)
    site_url: str
    path: str
    process_pages: bool = False
    recursive: bool = False

    def __post_init__(self):
        if not (self.client_id and self.client_credential and self.site_url):
            raise ValueError(
                "Please provide one of the following mandatory values:"
                "\n--client-id\n--client-cred\n--site",
            )

    @requires_dependencies(["office365"], extras="sharepoint")
    def get_site_client(self, site_url: str = "") -> "ClientContext":
        from office365.runtime.auth.client_credential import ClientCredential
        from office365.sharepoint.client_context import ClientContext

        try:
            site_client = ClientContext(site_url or self.site_url).with_credentials(
                ClientCredential(self.client_id, self.client_credential),
            )
        except Exception:
            logger.error("Couldn't set Sharepoint client.")
            raise
        return site_client


@dataclass
class SharepointIngestDoc(IngestDocCleanupMixin, BaseIngestDoc):
    connector_config: SimpleSharepointConfig
    site_url: str
    server_path: str
    is_page: bool
    file_path: str
    registry_name: str = "sharepoint"
    embedding_config: t.Optional[EmbeddingConfig] = None
    chunking_config: t.Optional[ChunkingConfig] = None

    def run_chunking(self, elements: t.List[Element]) -> t.List[Element]:
        if self.chunking_config:
            logger.info(
                "Running chunking to split up elements with config: "
                f"{self.chunking_config.to_dict()}",
            )
            chunked_elements = self.chunking_config.chunk(elements=elements)
            logger.info(f"chunked {len(elements)} elements into {len(chunked_elements)}")
            return chunked_elements
        else:
            return elements

    @property
    def embedder(self) -> t.Optional[BaseEmbeddingEncoder]:
        if self.embedding_config and self.embedding_config.api_key:
            return self.embedding_config.get_embedder()
        return None

    def __post_init__(self):
        self.extension = Path(self.file_path).suffix if not self.is_page else ".html"
        self.extension = ".html" if self.extension == ".aspx" else self.extension
        if not self.extension:
            raise ValueError("Unsupported file without extension.")

        if self.extension not in EXT_TO_FILETYPE:
            raise ValueError(
                f"Extension {self.extension} not supported. "
                f"Value MUST be one of {', '.join([k for k in EXT_TO_FILETYPE if k is not None])}.",
            )
        self._set_download_paths()

    def _set_download_paths(self) -> None:
        """Parses the folder structure from the source and creates the download and output paths"""
        download_path = Path(f"{self.read_config.download_dir}")
        output_path = Path(f"{self.partition_config.output_dir}")
        parent = Path(self.file_path).with_suffix(self.extension)
        self.download_dir = (download_path / parent.parent).resolve()
        self.download_filepath = (download_path / parent).resolve()
        output_filename = str(parent) + ".json"
        self.output_dir = (output_path / parent.parent).resolve()
        self.output_filepath = (output_path / output_filename).resolve()

    @property
    def filename(self):
        return Path(self.download_filepath).resolve()

    @property
    def _output_filename(self):
        return Path(self.output_filepath).resolve()

    @property
    def record_locator(self) -> t.Optional[t.Dict[str, t.Any]]:
        return {
            "server_path": self.server_path,
            "site_url": self.site_url,
        }

    @SourceConnectionError.wrap
    @requires_dependencies(["office365"], extras="sharepoint")
    def _fetch_file(self, properties_only: bool = False):
        """Retrieves the actual page/file from the Sharepoint instance"""
        from office365.runtime.client_request_exception import ClientRequestException

        site_client = self.connector_config.get_site_client(self.site_url)

        try:
            if self.is_page:
                file = site_client.web.get_file_by_server_relative_path("/" + self.server_path)
                file = file.listItemAllFields.select(CONTENT_LABELS).get().execute_query()
            else:
                file = site_client.web.get_file_by_server_relative_url(self.server_path)
                if properties_only:
                    file = file.get().execute_query()

        except ClientRequestException as e:
            if e.response.status_code == 404:
                return None
            raise
        return file

    def _fetch_page(self):
        site_client = self.connector_config.get_site_client(self.site_url)
        try:
            page = (
                site_client.site_pages.pages.get_by_url(self.server_path)
                .expand(["FirstPublished", "Modified", "Version"])
                .get()
                .execute_query()
            )
        except Exception as e:
            logger.error(f"Failed to retrieve page {self.server_path} from site {self.site_url}")
            logger.error(e)
            return None
        return page

    def update_source_metadata(self, **kwargs):
        if self.is_page:
            page = self._fetch_page()
            if page is None:
                self.source_metadata = SourceMetadata(
                    exists=False,
                )
                return
            self.source_metadata = SourceMetadata(
                date_created=page.get_property("FirstPublished", None),
                date_modified=page.get_property("Modified", None),
                version=page.get_property("Version", ""),
                source_url=page.absolute_url,
                exists=True,
            )
            return

        file = self._fetch_file(True)
        if file is None:
            self.source_metadata = SourceMetadata(
                exists=False,
            )
            return
        self.source_metadata = SourceMetadata(
            date_created=datetime.strptime(file.time_created, "%Y-%m-%dT%H:%M:%SZ").isoformat(),
            date_modified=datetime.strptime(
                file.time_last_modified,
                "%Y-%m-%dT%H:%M:%SZ",
            ).isoformat(),
            version=file.major_version,
            source_url=file.properties.get("LinkingUrl", None),
            exists=True,
        )

    def _download_page(self):
        """Formats and saves locally page content"""
        content = self._fetch_file()
        self.update_source_metadata()
        pld = (content.properties.get("LayoutWebpartsContent1", "") or "") + (
            content.properties.get("CanvasContent1", "") or ""
        )
        if pld != "":
            pld = unescape(pld)
        else:
            logger.info(
                f"Page {self.server_path} has no retrievable content. \
                    Dumping empty doc.",
            )
            pld = "<div></div>"

        self.output_dir.mkdir(parents=True, exist_ok=True)
        if not self.download_dir.is_dir():
            logger.debug(f"Creating directory: {self.download_dir}")
            self.download_dir.mkdir(parents=True, exist_ok=True)
        with self.filename.open(mode="w") as f:
            f.write(pld)
        logger.info(f"File downloaded: {self.filename}")

    def _download_file(self):
        file = self._fetch_file()
        self.update_source_metadata()
        fsize = file.length
        self.output_dir.mkdir(parents=True, exist_ok=True)

        if not self.download_dir.is_dir():
            logger.debug(f"Creating directory: {self.download_dir}")
            self.download_dir.mkdir(parents=True, exist_ok=True)

        if fsize > MAX_MB_SIZE:
            logger.info(f"Downloading file with size: {fsize} bytes in chunks")
            with self.filename.open(mode="wb") as f:
                file.download_session(f, chunk_size=1024 * 1024 * 100).execute_query()
        else:
            with self.filename.open(mode="wb") as f:
                file.download(f).execute_query()
        logger.info(f"File downloaded: {self.filename}")

    @BaseIngestDoc.skip_if_file_exists
    @requires_dependencies(["office365"])
    def get_file(self):
        if self.is_page:
            self._download_page()
        else:
            self._download_file()
        return


@dataclass
class SharepointSourceConnector(SourceConnectorCleanupMixin, BaseSourceConnector):
    connector_config: SimpleSharepointConfig
    embedding_config: t.Optional[EmbeddingConfig] = None
    chunking_config: t.Optional[ChunkingConfig] = None

    @requires_dependencies(["office365"], extras="sharepoint")
    def _list_files(self, folder, recursive) -> t.List["File"]:
        from office365.runtime.client_request_exception import ClientRequestException

        try:
            objects = folder.expand(["Files", "Folders"]).get().execute_query()
            files = list(objects.files)
            if not recursive:
                return files
            for f in objects.folders:
                if "/Forms" in f.serverRelativeUrl:
                    continue
                files += self._list_files(f, recursive)
            return files
        except ClientRequestException as e:
            if e.response.status_code != 404:
                logger.info("Caught an error while processing documents %s", e.response.text)
            return []

    def _prepare_ingest_doc(self, obj: t.Union["File", "SitePage"], base_url, is_page=False):
        if is_page:
            file_path = obj.get_property("Url", "")
            server_path = file_path if file_path[0] != "/" else file_path[1:]
            if (url_path := (urlparse(base_url).path)) and (url_path != "/"):
                file_path = url_path[1:] + "/" + file_path
        else:
            server_path = obj.serverRelativeUrl
            file_path = obj.serverRelativeUrl[1:]

        return SharepointIngestDoc(
            read_config=self.read_config,
            partition_config=self.partition_config,
            connector_config=self.connector_config,
            site_url=base_url,
            server_path=server_path,
            is_page=is_page,
            file_path=file_path,
            embedding_config=self.embedding_config,
            chunking_config=self.chunking_config,
        )

    @requires_dependencies(["office365"], extras="sharepoint")
    def _list_pages(self, site_client) -> list:
        from office365.runtime.client_request_exception import ClientRequestException

        try:
            site_pages = site_client.site_pages.pages.get().execute_query()
        except ClientRequestException as e:
            logger.info(
                "Caught an error while retrieving site pages from %s \n%s",
                site_client.base_url,
                e.response.text,
            )
            return []

        return [self._prepare_ingest_doc(page, site_client.base_url, True) for page in site_pages]

    def _ingest_site_docs(self, site_client) -> t.List["SharepointIngestDoc"]:
        root_folder = site_client.web.get_folder_by_server_relative_path(self.connector_config.path)
        files = self._list_files(root_folder, self.connector_config.recursive)
        if not files:
            logger.info(
                f"No processable files at path {self.connector_config.path}\
                for site {site_client.base_url}",
            )
        output = []
        for file in files:
            try:
                output.append(self._prepare_ingest_doc(file, site_client.base_url))
            except ValueError as e:
                logger.error("Unable to process file %s", file.properties["Name"])
                logger.error(e)
        if self.connector_config.process_pages:
            page_output = self._list_pages(site_client)
            if not page_output:
                logger.info(f"Couldn't process pages for site {site_client.base_url}")
            output = output + page_output
        return output

    def initialize(self):
        pass

    def get_ingest_docs(self):
        base_site_client = self.connector_config.get_site_client()
        if not base_site_client.is_tenant:
            return self._ingest_site_docs(base_site_client)
        tenant = base_site_client.tenant
        tenant_sites = tenant.get_site_properties_from_sharepoint_by_filters().execute_query()
        tenant_sites = {s.url for s in tenant_sites if (s.url is not None)}
        ingest_docs: t.List[SharepointIngestDoc] = []
        for site_url in tenant_sites:
            logger.info(f"Processing docs for site: {site_url}")
            site_client = self.connector_config.get_site_client(site_url)
            ingest_docs = ingest_docs + self._ingest_site_docs(site_client)
        return ingest_docs
