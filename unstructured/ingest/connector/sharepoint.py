from dataclasses import dataclass, field
from html import unescape
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional
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
    from office365.sharepoint.files.file import File

MAX_MB_SIZE = 512_000_000


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


@dataclass
class SharepointIngestDoc(IngestDocCleanupMixin, BaseIngestDoc):
    config: SimpleSharepointConfig
    file: "File"
    meta: dict

    def __post_init__(self):
        self.ext = "".join(Path(self.file.name).suffixes) if not self.meta else ".html"
        self.ext = self.ext if self.ext != ".aspx" else ".html"

        if not self.ext:
            raise ValueError("Unsupported file without extension.")

        if self.ext not in EXT_TO_FILETYPE:
            raise ValueError(
                f"Extension {self.ext} not supported. "
                f"Value MUST be one of {', '.join([k for k in EXT_TO_FILETYPE if k is not None])}.",
            )
        self._set_download_paths()

    def _set_download_paths(self) -> None:
        """Parses the folder structure from the source and creates the download and output paths"""
        download_path = Path(f"{self.standard_config.download_dir}")
        output_path = Path(f"{self.standard_config.output_dir}")
        if self.meta:
            page_url = self.meta["page"].get_property("Url", "")
            parent = (
                Path(page_url).with_suffix(self.ext)
                if (self.meta["site_path"] is None)
                else Path(self.meta["site_path"] + "/" + page_url).with_suffix(self.ext)
            )
        else:
            parent = Path(self.file.serverRelativeUrl[1:])
        self.download_dir = (download_path / parent.parent).resolve()
        self.download_filepath = (download_path / parent).resolve()
        oname = f"{str(parent)[:-len(self.ext)]}.json"
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
        if self.meta:
            return self.meta["page"].properties.get("FirstPublished", None)
        return self.file.time_created

    @property
    def date_modified(self) -> Optional[str]:
        if self.meta:
            return self.meta["page"].properties.get("Modified", None)
        return self.file.time_last_modified

    @property
    def exists(self) -> Optional[bool]:
        if self.meta:
            return self.meta["page"].properties.get("FileName", None) and self.meta[
                "page"
            ].properties.get("UniqueId", None)
        return self.file.exists

    @property
    def record_locator(self) -> Optional[Dict[str, Any]]:
        if self.meta:
            record_source = self.meta["page"]
            property_name = "AbsoluteUrl"
            resource_url_name = "absolute_url"
        else:
            record_source = self.file
            property_name = "ServerRelativeUrl"
            resource_url_name = "server_relative_url"

        return {
            "site": self.config.site_url,
            "unique_id": record_source.get_property("UniqueId", ""),
            resource_url_name: record_source.get_property(property_name, ""),
        }

    @property
    def version(self) -> Optional[str]:
        if self.meta:
            return self.meta["page"].properties.get("Version", "")

        if (n_versions := len(self.file.versions)) > 0:
            return self.file.versions[n_versions - 1].properties.get("id", None)
        return None

    def _get_page(self):
        """Retrieves HTML content of the Sharepoint site through the CanvasContent1 and
        LayoutWebpartsContent1"""

        try:
            content_labels = ["CanvasContent1", "LayoutWebpartsContent1"]
            content = self.file.listItemAllFields.select(content_labels).get().execute_query()
            pld = (content.properties.get("LayoutWebpartsContent1", "") or "") + (
                content.properties.get("CanvasContent1", "") or ""
            )
            if pld != "":
                pld = unescape(pld)
            else:
                logger.info(
                    f"Page {self.meta['page'].get_property('Url', '')} has no retrievable content. \
                      Dumping empty doc.",
                )
                pld = "<div></div>"

            self.output_dir.mkdir(parents=True, exist_ok=True)
            if not self.download_dir.is_dir():
                logger.debug(f"Creating directory: {self.download_dir}")
                self.download_dir.mkdir(parents=True, exist_ok=True)
            with self.filename.open(mode="w") as f:
                f.write(pld)
        except Exception as e:
            logger.error(f"Error while downloading and saving file: {self.filename}.")
            logger.error(e)
            return
        logger.info(f"File downloaded: {self.filename}")

    def _get_file(self):
        try:
            fsize = self.file.length
            self.output_dir.mkdir(parents=True, exist_ok=True)

            if not self.download_dir.is_dir():
                logger.debug(f"Creating directory: {self.download_dir}")
                self.download_dir.mkdir(parents=True, exist_ok=True)

            if fsize > MAX_MB_SIZE:
                logger.info(f"Downloading file with size: {fsize} bytes in chunks")
                with self.filename.open(mode="wb") as f:
                    self.file.download_session(f, chunk_size=1024 * 1024 * 100).execute_query()
            else:
                with self.filename.open(mode="wb") as f:
                    self.file.download(f).execute_query()
        except Exception as e:
            logger.error(f"Error while downloading and saving file: {self.filename}.")
            logger.error(e)
            return
        logger.info(f"File downloaded: {self.filename}")

    @BaseIngestDoc.skip_if_file_exists
    @requires_dependencies(["office365"])
    def get_file(self):
        if not self.meta:
            self._get_file()
        else:
            self._get_page()
        return


class SharepointConnector(ConnectorCleanupMixin, BaseConnector):
    config: SimpleSharepointConfig
    tenant: None

    def __init__(self, standard_config: StandardConnectorConfig, config: SimpleSharepointConfig):
        super().__init__(standard_config, config)
        self._setup_client()

    @requires_dependencies(["office365"])
    def _setup_client(self):
        from office365.runtime.auth.client_credential import ClientCredential
        from office365.sharepoint.client_context import ClientContext

        parsed_url = urlparse(self.config.site_url)
        site_hostname = (parsed_url.hostname or "").split(".")
        tenant_url = site_hostname[0].split("-")
        self.process_all = False
        self.base_site_url = ""
        if tenant_url[-1] == "admin" and (parsed_url.path is None or parsed_url.path == "/"):
            self.process_all = True
            self.base_site_url = parsed_url._replace(
                netloc=parsed_url.netloc.replace(site_hostname[0], tenant_url[0]),
            ).geturl()
        elif tenant_url[-1] == "admin":
            raise ValueError(
                "A site url in the form of https://[tenant]-admin.sharepoint.com \
                is required to process all sites within a tenant. ",
            )

        self.client = ClientContext(self.config.site_url).with_credentials(
            ClientCredential(self.config.client_id, self.config.client_credential),
        )

    @requires_dependencies(["office365"])
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

    @requires_dependencies(["office365"])
    def _list_pages(self, site_client) -> list:
        from office365.runtime.client_request_exception import ClientRequestException

        try:
            pages = site_client.site_pages.pages.get().execute_query()
            page_files = []

            for page_meta in pages:
                page_url = page_meta.get_property("Url", None)
                if page_url is None:
                    logger.info("Missing site_url. Omitting page... ")
                    break
                page_url = f"/{page_url}" if page_url[0] != "/" else page_url
                file_page = site_client.web.get_file_by_server_relative_path(page_url)
                site_path = None
                if (url_path := (urlparse(site_client.base_url).path)) and (url_path != "/"):
                    site_path = url_path[1:]
                page_files.append(
                    [file_page, {"page": page_meta, "site_path": site_path}],
                )
        except ClientRequestException as e:
            logger.info("Caught an error while processing pages %s", e.response.text)
            return []

        return page_files

    def initialize(self):
        pass

    def _ingest_site_docs(self, site_client) -> List["SharepointIngestDoc"]:
        root_folder = site_client.web.get_folder_by_server_relative_path(self.config.path)
        files = self._list_files(root_folder, self.config.recursive)
        if not files:
            logger.info(
                f"Couldn't process files in path {self.config.path} \
                for site {site_client.base_url}",
            )
        output = [SharepointIngestDoc(self.standard_config, self.config, f, {}) for f in files]
        if self.config.process_pages:
            page_files = self._list_pages(site_client)
            if not page_files:
                logger.info(f"Couldn't process pages for site {site_client.base_url}")
            page_output = [
                SharepointIngestDoc(self.standard_config, self.config, f[0], f[1])
                for f in page_files
            ]
            output = output + page_output
        return output

    def _filter_site_url(self, site):
        if site.url is None:
            return False
        return (site.url[0 : len(self.base_site_url)] == self.base_site_url) and (  # noqa: E203
            "/sites/" in site.url
        )

    @requires_dependencies(["office365"])
    def get_ingest_docs(self):
        if self.process_all:
            logger.debug(self.base_site_url)
            from office365.runtime.auth.client_credential import ClientCredential
            from office365.sharepoint.client_context import ClientContext
            from office365.sharepoint.tenant.administration.tenant import Tenant

            tenant = Tenant(self.client)
            tenant_sites = tenant.get_site_properties_from_sharepoint_by_filters().execute_query()
            tenant_sites = [s.url for s in tenant_sites if self._filter_site_url(s)]
            tenant_sites.append(self.base_site_url)
            ingest_docs: List[SharepointIngestDoc] = []
            for site_url in set(tenant_sites):
                logger.info(f"Processing docs for site: {site_url}")
                site_client = ClientContext(site_url).with_credentials(
                    ClientCredential(self.config.client_id, self.config.client_credential),
                )
                ingest_docs = ingest_docs + self._ingest_site_docs(site_client)
            return ingest_docs
        else:
            return self._ingest_site_docs(self.client)
