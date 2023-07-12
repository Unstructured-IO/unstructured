from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, List

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
    from office365.sharepoint.publishing.pages.page import SitePage

MAX_MB_SIZE = 512_000_000


@dataclass
class SimpleSharepointConfig(BaseConnectorConfig):
    client_id: str
    client_credential: str = field(repr=False)
    site_url: str
    folder: str
    process_pages: bool = False
    recursive: bool = False

    def __post_init__(self):
        if not (self.client_id and self.client_credential and self.site_url):
            raise ValueError(
                "Please provide one of the following mandatory values:"
                "\n-ms-client_id\n-ms-client_cred\n-ms-sharepoint-site",
            )


@dataclass
class SharepointIngestDoc(IngestDocCleanupMixin, BaseIngestDoc):
    config: SimpleSharepointConfig
    file: "File"
    meta: any

    def __post_init__(self):
        self.ext = "".join(Path(self.file.name).suffixes) if self.meta is None else '.html'
        if not self.ext:
            raise ValueError("Unsupported file without extension.")

        if self.ext not in EXT_TO_FILETYPE.keys():
            raise ValueError(
                f"Extension not supported. "
                f"Value MUST be one of {', '.join([k for k in EXT_TO_FILETYPE if k is not None])}.",
            )        
        self._set_download_paths()

    def _set_download_paths(self) -> None:
        """Parses the folder structure from the source and creates the download and output paths"""
        download_path = Path(f"{self.standard_config.download_dir}")
        output_path = Path(f"{self.standard_config.output_dir}")
        parent = Path(self.file.serverRelativeUrl[1:]) if self.meta is None else \
            Path(self.meta.get_property('Url', '')).with_suffix(self.ext)
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

    def _get_page(self):
        try:
            content_labels = ["CanvasContent1"]
            content = self.file.listItemAllFields.select(content_labels).get().execute_query()
            pld = ''
            for label in content_labels:
                c = content.properties.get(label, '')
                pld = pld if not c else pld+c

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
            fsize = self.file.get_property("size", 0)
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
        if self.meta is None:
            self._get_file()
        else:
            self._get_page()
        return


class SharepointConnector(ConnectorCleanupMixin, BaseConnector):
    config: SimpleSharepointConfig

    def __init__(self, standard_config: StandardConnectorConfig, config: SimpleSharepointConfig):
        super().__init__(standard_config, config)
        self._set_client()

    @requires_dependencies(["office365"])
    def _set_client(self):
        from office365.runtime.auth.client_credential import ClientCredential
        from office365.sharepoint.client_context import ClientContext

        self.client = ClientContext(self.config.site_url).with_credentials(
            ClientCredential(self.config.client_id, self.config.client_credential)
        )

    def _list_files(self, root, recursive) -> List["File"]:
        folder = root.expand(["Files", "Folders"]).get().execute_query()
        files = list(folder.files)
        if not recursive:
            return files
        for f in folder.folders:
            files += self._list_objects(f, recursive)
        return files

    def _list_pages(self) -> List["File"]:
        pages = self.client.site_pages.pages.get().execute_query()
        pfiles = []
        for page_meta in pages:
            site_url = page_meta.get_property('Url', None)
            if site_url is None:
                logger.info('Missing site_url. Omitting page... ')
                break
            site_url = f'/{site_url}' if site_url[0] != '/' else site_url
            file_page = self.client.web.get_file_by_server_relative_path(site_url)
            pfiles.append([file_page, page_meta])

        return pfiles

    def initialize(self):
        pass

    def get_ingest_docs(self):
        root_folder = self.client.web.get_folder_by_server_relative_path(self.config.folder)
        files = self._list_files(root_folder, self.config.recursive)
        file_output = [SharepointIngestDoc(self.standard_config, self.config, f, None) for f in files]
        if self.config.process_pages:
            page_files = self._list_pages()
            page_output = [SharepointIngestDoc(self.standard_config, self.config, f[0], f[1]) for f in page_files]
        return file_output + page_output
