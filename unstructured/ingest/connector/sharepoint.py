import json
import os
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
    application_id_rbac: str
    client_cred_rbac: str = field(repr=False)
    rbac_tenant: str
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

    def get_rbac_client(self):
        try:
            rbac_connector = ConnectorRBAC(
                self.rbac_tenant,
                self.application_id_rbac,
                self.client_cred_rbac,
            )
            assert rbac_connector.access_token
            return rbac_connector
        except Exception as e:
            logger.error("Couldn't obtain Sharepoint RBAC ingestion access token:", e)


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

    # todo: improve rbac - ingestdoc matching logic
    # todo: better folder management for writing down the rbac data
    # todo: obtain rbac_data field as a python dict and serialise after, rather than a direct str
    def update_rbac_data(self):
        self._rbac_data = ""
        if self.output_dir.is_dir():
            for filename in os.listdir(self.partition_config.output_dir):
                if self.file_path.split("/")[-1] in filename:
                    with open(os.path.join(self.partition_config.output_dir, filename)) as f:
                        self._rbac_data = f.read()

    def update_source_metadata(self, **kwargs):
        self.update_rbac_data()
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
                rbac_data=self._rbac_data,
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
            rbac_data=self._rbac_data,
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

        if self.connector_config.application_id_rbac:
            rbac_client = self.connector_config.get_rbac_client()
            if rbac_client:
                rbac_client.write_all_permissions(self.partition_config.output_dir)

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


class ConnectorRBAC:
    def __init__(self, rbac_tenant, application_id_rbac, client_cred_rbac):
        self.rbac_tenant = rbac_tenant
        self.application_id_rbac = application_id_rbac
        self.client_cred_rbac = client_cred_rbac
        self.access_token = self.get_access_token()

    @requires_dependencies(["requests"], extras="sharepoint")
    def get_access_token(self):
        import requests

        url = f"https://login.microsoftonline.com/{self.rbac_tenant}/oauth2/v2.0/token"
        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        data = {
            "client_id": self.application_id_rbac,
            "scope": "https://graph.microsoft.com/.default",
            "client_secret": self.client_cred_rbac,
            "grant_type": "client_credentials",
        }

        response = requests.post(url, headers=headers, data=data)
        return response.json()["access_token"]

    def validated_response(self, response):
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Request failed with status code {response.status_code}:")
            print(response.text)

    @requires_dependencies(["requests"], extras="sharepoint")
    def get_sites(self):
        import requests

        url = "https://graph.microsoft.com/v1.0/sites"
        params = {
            "$select": "webUrl, id",
        }

        headers = {
            "Authorization": f"Bearer {self.access_token}",
        }

        response = requests.get(url, params=params, headers=headers)
        return self.validated_response(response)

    @requires_dependencies(["requests"], extras="sharepoint")
    def get_drives(self, site):
        import requests

        url = f"https://graph.microsoft.com/v1.0/sites/{site}/drives"

        headers = {
            "Authorization": f"Bearer {self.access_token}",
        }

        response = requests.get(url, headers=headers)

        return self.validated_response(response)

    @requires_dependencies(["requests"], extras="sharepoint")
    def get_drive_items(self, site, drive_id):
        import requests

        url = f"https://graph.microsoft.com/v1.0/sites/{site}/drives/{drive_id}/root/children"

        headers = {
            "Authorization": f"Bearer {self.access_token}",
        }

        response = requests.get(url, headers=headers)

        return self.validated_response(response)

    @requires_dependencies(["requests"], extras="sharepoint")
    def get_permissions_for_drive_item(self, site, drive_id, item_id):
        import requests

        url = f"https://graph.microsoft.com/v1.0/sites/ \
        {site}/drives/{drive_id}/items/{item_id}/permissions"

        headers = {
            "Authorization": f"Bearer {self.access_token}",
        }

        response = requests.get(url, headers=headers)

        return self.validated_response(response)

    def write_all_permissions(self, output_dir):
        sites = [(site["id"], site["webUrl"]) for site in self.get_sites()["value"]]
        drive_ids = []

        print("Obtaining drive data for sites for RBAC")
        for site_id, site_url in sites:
            drives = self.get_drives(site_id)
            if drives:
                drives_for_site = drives["value"]
                drive_ids.extend([(site_id, drive["id"]) for drive in drives_for_site])

        print("Obtaining item data from drives for RBAC")
        item_ids = []
        for site, drive_id in drive_ids:
            drive_items = self.get_drive_items(site, drive_id)
            if drive_items:
                item_ids.extend(
                    [(site, drive_id, item["id"], item["name"]) for item in drive_items["value"]],
                )

        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        print("Writing RBAC data to disk")
        for site, drive_id, item_id, item_name in item_ids:
            with open(output_dir + "/" + item_name + "_" + item_id + ".json", "w") as f:
                res = self.get_permissions_for_drive_item(site, drive_id, item_id)
                if res:
                    json.dump(res["value"], f)
