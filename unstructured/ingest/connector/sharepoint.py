import typing as t
from dataclasses import dataclass, field
from html import unescape
from pathlib import Path
from urllib.parse import urlparse

from unstructured.file_utils.filetype import EXT_TO_FILETYPE
from unstructured.ingest.error import SourceConnectionError
from unstructured.ingest.interfaces import (
    BaseConnectorConfig,
    BaseIngestDoc,
    BaseSourceConnector,
    IngestDocCleanupMixin,
    SourceConnectorCleanupMixin,
)
from unstructured.ingest.logger import logger
from unstructured.utils import requires_dependencies

if t.TYPE_CHECKING:
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
    connector_config: SimpleSharepointConfig
    site_url: str
    server_path: str
    is_page: bool
    file_path: str
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
        self.file_exists = False
        self._set_download_paths()

    def _set_download_paths(self) -> None:
        """Parses the folder structure from the source and creates the download and output paths"""
        download_path = Path(f"{self.read_config.download_dir}")
        output_path = Path(f"{self.partition_config.output_dir}")
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

    # TODO: address data source properties in explicit PR

    def _get_page(self):
        """Retrieves HTML content of the Sharepoint site through the CanvasContent1 and
        LayoutWebpartsContent1"""
        from office365.runtime.auth.client_credential import ClientCredential
        from office365.sharepoint.client_context import ClientContext

        try:
            site_client = ClientContext(self.site_url).with_credentials(
                ClientCredential(
                    self.connector_config.client_id,
                    self.connector_config.client_credential,
                ),
            )
            file = site_client.web.get_file_by_server_relative_path(self.server_path)
            self.file_exists = True
            content_labels = ["CanvasContent1", "LayoutWebpartsContent1"]
            content = file.listItemAllFields.select(content_labels).get().execute_query()
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
        except Exception as e:
            logger.error(f"Error while downloading and saving file: {self.filename}.")
            logger.error(e)
            self.file_exists = False
            return
        logger.info(f"File downloaded: {self.filename}")

    @SourceConnectionError.wrap
    @requires_dependencies(["office365"], extras="sharepoint")
    def _get_file(self):
        from office365.runtime.auth.client_credential import ClientCredential
        from office365.sharepoint.client_context import ClientContext

        try:
            site_client = ClientContext(self.site_url).with_credentials(
                ClientCredential(
                    self.connector_config.client_id,
                    self.connector_config.client_credential,
                ),
            )
            file = site_client.web.get_file_by_server_relative_url(self.server_path)
            self.file_exists = True
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
        except Exception as e:
            logger.error(f"Error while downloading and saving file: {self.filename}.")
            logger.error(e)
            self.file_exists = False
            return
        logger.info(f"File downloaded: {self.filename}")

    @BaseIngestDoc.skip_if_file_exists
    @requires_dependencies(["office365"])
    def get_file(self):
        if self.is_page:
            self._get_page()
        else:
            self._get_file()
        return


@dataclass
class SharepointSourceConnector(SourceConnectorCleanupMixin, BaseSourceConnector):
    connector_config: SimpleSharepointConfig

    def initialize(self):
        self._setup_client()

    @requires_dependencies(["office365"], extras="sharepoint")
    def _setup_client(self):
        from office365.runtime.auth.client_credential import ClientCredential
        from office365.sharepoint.client_context import ClientContext

        parsed_url = urlparse(self.connector_config.site_url)
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

        self.client = ClientContext(self.connector_config.site_url).with_credentials(
            ClientCredential(
                self.connector_config.client_id,
                self.connector_config.client_credential,
            ),
        )

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

        pages = []
        for page in site_pages:
            try:
                page_url = page.get_property("Url", "")
                page_url = f"/{page_url}" if page_url[0] != "/" else page_url
                file_path = page.get_property("Url", "")
                if (url_path := (urlparse(site_client.base_url).path)) and (url_path != "/"):
                    file_path = url_path[1:] + "/" + file_path
                pages.append(
                    SharepointIngestDoc(
                        connector_config=self.connector_config,
                        partition_config=self.partition_config,
                        read_config=self.read_config,
                        site_url=site_client.base_url,
                        server_path=page_url,
                        is_page=True,
                        file_path=file_path,
                    ),
                )
            except Exception as e:
                logger.info("Omitting page %s. Caught error: \n%s", page_url, e)
                continue
        return pages

    def _ingest_site_docs(self, site_client) -> t.List["SharepointIngestDoc"]:
        root_folder = site_client.web.get_folder_by_server_relative_path(self.connector_config.path)
        files = self._list_files(root_folder, self.connector_config.recursive)
        if not files:
            logger.info(
                f"Couldn't process files in path {self.connector_config.path} \
                for site {site_client.base_url}",
            )
        output = []
        for file in files:
            try:
                print(file.serverRelativeUrl)
                output.append(
                    SharepointIngestDoc(
                        connector_config=self.connector_config,
                        partition_config=self.partition_config,
                        read_config=self.read_config,
                        site_url=site_client.base_url,
                        server_path=file.serverRelativeUrl,
                        is_page=False,
                        file_path=file.serverRelativeUrl[1:],
                    ),
                )
            except Exception as e:
                logger.info("Omitting file %s. Caught error: \n%s", file.name, e)
                continue

        if self.connector_config.process_pages:
            page_output = self._list_pages(site_client)
            if not page_output:
                logger.info(f"Couldn't process pages for site {site_client.base_url}")
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
            ingest_docs: t.List[SharepointIngestDoc] = []
            for site_url in set(tenant_sites):
                logger.info(f"Processing docs for site: {site_url}")
                site_client = ClientContext(site_url).with_credentials(
                    ClientCredential(
                        self.connector_config.client_id,
                        self.connector_config.client_credential,
                    ),
                )
                ingest_docs = ingest_docs + self._ingest_site_docs(site_client)
            return ingest_docs
        else:
            return self._ingest_site_docs(self.client)
