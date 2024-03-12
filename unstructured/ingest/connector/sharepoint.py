import json
import os
import typing as t
from dataclasses import dataclass
from html import unescape
from pathlib import Path
from urllib.parse import urlparse

from unstructured.file_utils.filetype import EXT_TO_FILETYPE
from unstructured.ingest.enhanced_dataclass import enhanced_field
from unstructured.ingest.error import SourceConnectionError, SourceConnectionNetworkError
from unstructured.ingest.interfaces import (
    AccessConfig,
    BaseConnectorConfig,
    BaseSingleIngestDoc,
    BaseSourceConnector,
    IngestDocCleanupMixin,
    SourceConnectorCleanupMixin,
    SourceMetadata,
)
from unstructured.ingest.interfaces import PermissionsConfig as SharepointPermissionsConfig
from unstructured.ingest.logger import logger
from unstructured.ingest.utils.string_and_date_utils import ensure_isoformat_datetime
from unstructured.utils import requires_dependencies

if t.TYPE_CHECKING:
    from office365.sharepoint.client_context import ClientContext
    from office365.sharepoint.files.file import File
    from office365.sharepoint.publishing.pages.page import SitePage

MAX_MB_SIZE = 512_000_000
CONTENT_LABELS = ["CanvasContent1", "LayoutWebpartsContent1", "TimeCreated"]


@dataclass
class SharepointAccessConfig(AccessConfig):
    client_cred: str = enhanced_field(repr=False, sensitive=True)


@dataclass
class SimpleSharepointConfig(BaseConnectorConfig):
    access_config: SharepointAccessConfig
    client_id: str
    site: str
    path: str
    process_pages: bool = enhanced_field(default=True, init=False)
    recursive: bool = False
    files_only: bool = False
    permissions_config: t.Optional[SharepointPermissionsConfig] = None

    def __post_init__(self):
        if not (self.client_id and self.access_config.client_cred and self.site):
            raise ValueError(
                "Please provide one of the following mandatory values:"
                "\n--client-id\n--client-cred\n--site",
            )
        self.process_pages = not self.files_only

    @requires_dependencies(["office365"], extras="sharepoint")
    def get_site_client(self, site_url: str = "") -> "ClientContext":
        from office365.runtime.auth.client_credential import ClientCredential
        from office365.sharepoint.client_context import ClientContext

        try:
            site_client = ClientContext(site_url or self.site).with_credentials(
                ClientCredential(self.client_id, self.access_config.client_cred),
            )
        except Exception:
            logger.error("Couldn't set Sharepoint client.")
            raise
        return site_client

    def get_permissions_client(self):
        try:
            permissions_connector = SharepointPermissionsConnector(self.permissions_config)
            assert permissions_connector.access_token
            return permissions_connector
        except Exception as e:
            logger.error("Couldn't obtain Sharepoint permissions ingestion access token:", e)


@dataclass
class SharepointIngestDoc(IngestDocCleanupMixin, BaseSingleIngestDoc):
    connector_config: SimpleSharepointConfig
    site_url: str
    server_path: str
    is_page: bool
    file_path: str
    registry_name: str = "sharepoint"

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
        output_path = Path(f"{self.processor_config.output_dir}")
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

    @SourceConnectionNetworkError.wrap
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

    def update_permissions_data(self):
        def parent_name_matches(parent_type, permissions_filename, ingest_doc_filepath):
            permissions_filename = permissions_filename.split("_SEP_")
            ingest_doc_filepath = ingest_doc_filepath.split("/")

            if parent_type == "sites":
                return permissions_filename[0] == ingest_doc_filepath[1]

            elif parent_type == "SitePages" or parent_type == "Shared Documents":
                return True

        permissions_data = None
        permissions_dir = Path(self.processor_config.output_dir) / "permissions_data"

        if permissions_dir.is_dir():
            parent_type = self.file_path.split("/")[0]

            if parent_type == "sites":
                read_dir = permissions_dir / "sites"
            elif parent_type == "SitePages" or parent_type == "Shared Documents":
                read_dir = permissions_dir / "other"
            else:
                read_dir = permissions_dir / "other"

            for filename in os.listdir(read_dir):
                permissions_docname = os.path.splitext(filename)[0].split("_SEP_")[1]
                ingestdoc_docname = self.file_path.split("/")[-1]

                if ingestdoc_docname == permissions_docname and parent_name_matches(
                    parent_type=parent_type,
                    permissions_filename=filename,
                    ingest_doc_filepath=self.file_path,
                ):
                    with open(read_dir / filename) as f:
                        permissions_data = json.loads(f.read())

        return permissions_data

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
                permissions_data=(
                    self.update_permissions_data()
                    if self.connector_config.permissions_config
                    else None
                ),
            )
            return

        file = self._fetch_file(True)
        if file is None:
            self.source_metadata = SourceMetadata(
                exists=False,
            )
            return
        self.source_metadata = SourceMetadata(
            date_created=ensure_isoformat_datetime(timestamp=file.time_created),
            date_modified=ensure_isoformat_datetime(timestamp=file.time_last_modified),
            version=file.major_version,
            source_url=file.properties.get("LinkingUrl", None),
            exists=True,
            permissions_data=(
                self.update_permissions_data() if self.connector_config.permissions_config else None
            ),
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

    @BaseSingleIngestDoc.skip_if_file_exists
    @SourceConnectionError.wrap
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

    def check_connection(self):
        try:
            site_client = self.connector_config.get_site_client()
            site_client.site_pages.pages.get().execute_query()
        except Exception as e:
            logger.error(f"failed to validate connection: {e}", exc_info=True)
            raise SourceConnectionError(f"failed to validate connection: {e}")

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
            processor_config=self.processor_config,
            read_config=self.read_config,
            connector_config=self.connector_config,
            site_url=base_url,
            server_path=server_path,
            is_page=is_page,
            file_path=file_path,
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

        if not all(
            getattr(self.connector_config.permissions_config, attr, False)
            for attr in ["application_id", "client_cred", "tenant"]
        ):
            logger.info(
                "Permissions config is not fed with 'application_id', 'client_cred' and 'tenant'."
                "Skipping permissions ingestion.",
            )
        else:
            permissions_client = self.connector_config.get_permissions_client()
            if permissions_client:
                permissions_client.write_all_permissions(self.processor_config.output_dir)

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


@dataclass
class SharepointPermissionsConnector:
    def __init__(self, permissions_config):
        self.permissions_config: SharepointPermissionsConfig = permissions_config
        self.initialize()

    def initialize(self):
        self.access_token: str = self.get_access_token()

    @requires_dependencies(["requests"], extras="sharepoint")
    def get_access_token(self) -> str:
        import requests

        url = (
            f"https://login.microsoftonline.com/{self.permissions_config.tenant}/oauth2/v2.0/token"
        )
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        data = {
            "client_id": self.permissions_config.application_id,
            "scope": "https://graph.microsoft.com/.default",
            "client_secret": self.permissions_config.client_cred,
            "grant_type": "client_credentials",
        }
        response = requests.post(url, headers=headers, data=data)
        return response.json()["access_token"]

    def validated_response(self, response):
        if response.status_code == 200:
            return response.json()
        else:
            logger.info(f"Request failed with status code {response.status_code}:")
            logger.info(response.text)

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

    def extract_site_name_from_weburl(self, weburl):
        split_path = urlparse(weburl).path.lstrip("/").split("/")

        if split_path[0] == "sites":
            return "sites", split_path[1]

        elif split_path[0] == "Shared%20Documents":
            return "Shared Documents", "Shared Documents"

        elif split_path[0] == "personal":
            return "Personal", "Personal"

        elif split_path[0] == "_layouts":
            return "layouts", "layouts"

        # if other weburl structures are found, additional logic might need to be implemented

        logger.warning(
            """Couldn't extract sitename, unknown site or parent type. Skipping permissions
            ingestion for the document with the URL:""",
            weburl,
        )

        return None, None

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

        logger.info("Obtaining drive data for sites for permissions (rbac)")
        for site_id, site_url in sites:
            drives = self.get_drives(site_id)
            if drives:
                drives_for_site = drives["value"]
                drive_ids.extend([(site_id, drive["id"]) for drive in drives_for_site])

        logger.info("Obtaining item data from drives for permissions (rbac)")
        item_ids = []
        for site, drive_id in drive_ids:
            drive_items = self.get_drive_items(site, drive_id)
            if drive_items:
                item_ids.extend(
                    [
                        (site, drive_id, item["id"], item["name"], item["webUrl"])
                        for item in drive_items["value"]
                    ],
                )

        permissions_dir = Path(output_dir) / "permissions_data"

        logger.info("Writing permissions data to disk")
        for site, drive_id, item_id, item_name, item_web_url in item_ids:
            res = self.get_permissions_for_drive_item(site, drive_id, item_id)
            if res:
                parent_type, parent_name = self.extract_site_name_from_weburl(item_web_url)

                if parent_type == "sites":
                    write_path = permissions_dir / "sites" / f"{parent_name}_SEP_{item_name}.json"

                elif parent_type == "Personal" or parent_type == "Shared Documents":
                    write_path = permissions_dir / "other" / f"{parent_name}_SEP_{item_name}.json"
                else:
                    write_path = permissions_dir / "other" / f"{parent_name}_SEP_{item_name}.json"

                if not Path(os.path.dirname(write_path)).is_dir():
                    os.makedirs(os.path.dirname(write_path))

                with open(write_path, "w") as f:
                    json.dump(res["value"], f)
