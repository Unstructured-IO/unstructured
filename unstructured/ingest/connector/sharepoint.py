from dataclasses import dataclass, field
from datetime import datetime
from html import unescape
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union
from urllib.parse import urlparse

from unstructured.file_utils.filetype import EXT_TO_FILETYPE
from unstructured.ingest.interfaces import (
    BaseConnector,
    BaseConnectorConfig,
    BaseIngestDoc,
    ConnectorCleanupMixin,
    IngestDocCleanupMixin,
    StandardConnectorConfig,
)
from unstructured.ingest.logger import logger
from unstructured.utils import requires_dependencies

if TYPE_CHECKING:
    from office365.sharepoint.client_context import ClientContext
    from office365.sharepoint.files.file import File
    from office365.sharepoint.publishing.pages.page import SitePage

MAX_MB_SIZE = 512_000_000
CONTENT_LABELS = ["CanvasContent1", "LayoutWebpartsContent1"]


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
class SharepointFileMeta:
    date_created: str
    date_modified: str
    version: str


@dataclass
class SharepointIngestDoc(IngestDocCleanupMixin, BaseIngestDoc):
    config: SimpleSharepointConfig
    site_url: str
    server_path: str
    is_page: bool
    file_path: str
    file_exists: Optional[bool] = None
    file_meta: Optional[SharepointFileMeta] = None
    registry_name: str = "sharepoint"

    def __post_init__(self):
        self.extension = "".join(Path(self.file_path).suffixes) if not self.is_page else ".html"
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
        download_path = Path(f"{self.standard_config.download_dir}")
        output_path = Path(f"{self.standard_config.output_dir}")
        parent = Path(self.file_path).with_suffix(self.extension)
        self.download_dir = (download_path / parent.parent).resolve()
        self.download_filepath = (download_path / parent).resolve()
        oname = f"{str(parent)[:-len(self.extension)]}.json"
        self.output_dir = (output_path / parent.parent).resolve()
        self.output_filepath = (output_path / oname).resolve()

    @property
    def filename(self):
        return Path(self.download_filepath).resolve()

    @property
    def _output_filename(self):
        return Path(self.output_filepath).resolve()

    @property
    def date_created(self) -> Optional[str]:
        if self.file_meta is None:
            self.get_file_metadata()
        return self.file_meta.date_created  # type: ignore

    @property
    def date_modified(self) -> Optional[str]:
        if self.file_meta is None:
            self.get_file_metadata()
        return self.file_meta.date_modified  # type: ignore

    @property
    def exists(self) -> Optional[bool]:
        if self.file_exists is None:
            self.get_file_metadata()
        return self.file_exists

    @property
    def record_locator(self) -> Optional[Dict[str, Any]]:
        return {
            "server_path": self.server_path,
            "site_url": self.site_url,
        }

    @property
    def version(self) -> Optional[str]:
        if self.file_meta is None:
            self.get_file_metadata()
        return self.file_meta.version  # type: ignore

    @requires_dependencies(["office365"], extras="sharepoint")
    def _fetch_file(self):
        """Retrieves the actual page/file from the Sharepoint instance"""
        from office365.runtime.client_request_exception import ClientRequestException

        site_client = self.config.get_site_client(self.site_url)

        try:
            if self.is_page:
                file = site_client.web.get_file_by_server_relative_path(self.server_path)
            else:
                file = site_client.web.get_file_by_server_relative_url(self.server_path)

        except ClientRequestException as e:
            if e.response.status_code == 404:
                self.file_exists = False
            raise
        self.file_exists = True
        return file

    def _fetch_page(self):
        site_client = self.config.get_site_client(self.site_url)
        try:
            page = site_client.site_pages.pages.get_by_url(self.server_path)
        except Exception as e:
            logger.error(f"Failed to retrieve page {self.server_path} from site {self.server_path}")
            logger.error(e)
            return None
        return page

    @requires_dependencies(["office365"], extras="sharepoint")
    def get_file_metadata(self, file=None):
        if file is None:
            file = self._fetch_file()
        if not self.is_page:
            self.file_meta = SharepointFileMeta(
                datetime.strptime(file.time_created, "%Y-%m-%dT%H:%M:%S.%fZ").isoformat(),
                datetime.strptime(file.time_last_modified, "%Y-%m-%dT%H:%M:%S.%fZ").isoformat(),
                file.major_version,
            )
        else:
            page = self._fetch_page()
            if page is None:
                return
            self.file_meta = SharepointFileMeta(
                page.get_property("FirstPublished", None),
                page.get_property("Modified", None),
                page.get_property("Version", ""),
            )

    def _download_page(self):
        """Formats and saves locally page content"""
        file = self._fetch_file()
        self.get_file_metadata(file)
        content = file.listItemAllFields.select(CONTENT_LABELS).get().execute_query()
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
        self.get_file_metadata(file)
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


class SharepointConnector(ConnectorCleanupMixin, BaseConnector):
    config: SimpleSharepointConfig
    tenant: None

    def __init__(self, standard_config: StandardConnectorConfig, config: SimpleSharepointConfig):
        super().__init__(standard_config, config)

    @requires_dependencies(["office365"], extras="sharepoint")
    def _list_files(self, folder, recursive) -> List["File"]:
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

    def _prepare_ingest_doc(self, obj: Union["File", "SitePage"], base_url, is_page=False):
        if is_page:
            file_path = obj.get_property("Url", "")
            server_path = f"/{file_path}" if file_path[0] != "/" else file_path
            if (url_path := (urlparse(base_url).path)) and (url_path != "/"):
                file_path = url_path[1:] + "/" + file_path
        else:
            server_path = obj.serverRelativeUrl
            file_path = obj.serverRelativeUrl[1:]

        return SharepointIngestDoc(
            self.standard_config,
            self.config,
            base_url,
            server_path,
            True,
            file_path,
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

    def _ingest_site_docs(self, site_client) -> List["SharepointIngestDoc"]:
        root_folder = site_client.web.get_folder_by_server_relative_path(self.config.path)
        files = self._list_files(root_folder, self.config.recursive)
        if not files:
            logger.info(
                f"Couldn't process files in path {self.config.path}\
                for site {site_client.base_url}",
            )
        output = [self._prepare_ingest_doc(file, site_client.base_url) for file in files]
        if self.config.process_pages:
            page_output = self._list_pages(site_client)
            if not page_output:
                logger.info(f"Couldn't process pages for site {site_client.base_url}")
            output = output + page_output
        return output

    def initialize(self):
        pass

    def get_ingest_docs(self):
        base_site_client = self.config.get_site_client()
        if not base_site_client.is_tenant:
            return self._ingest_site_docs(base_site_client)
        tenant = base_site_client.tenant
        tenant_sites = tenant.get_site_properties_from_sharepoint_by_filters().execute_query()
        tenant_sites = {s.url for s in tenant_sites if (s.url is not None)}
        ingest_docs: List[SharepointIngestDoc] = []
        for site_url in tenant_sites:
            logger.info(f"Processing docs for site: {site_url}")
            site_client = self.config.get_site_client(site_url)
            ingest_docs = ingest_docs + self._ingest_site_docs(site_client)
        return ingest_docs
