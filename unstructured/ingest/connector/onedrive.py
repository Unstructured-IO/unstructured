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
    from office365.onedrive.driveitems.driveItem import DriveItem

MAX_MB_SIZE = 512_000_000


@dataclass
class SimpleOneDriveConfig(BaseConnectorConfig):
    client_id: str
    client_credential: str = field(repr=False)
    user_pname: str
    tenant: str = field(repr=False)
    authority_url: str = field(repr=False)
    folder: str = field(default="")
    recursive: bool = False

    def __post_init__(self):
        if not (self.client_id and self.client_credential and self.user_pname):
            raise ValueError(
                "Please provide one of the following mandatory values:"
                "\n-ms-client_id\n-ms-client_cred\n-ms-user-pname",
            )
        self.token_factory = self._acquire_token

    @requires_dependencies(["msal"])
    def _acquire_token(self):
        from msal import ConfidentialClientApplication

        try:
            app = ConfidentialClientApplication(
                authority=f"{self.authority_url}/{self.tenant}",
                client_id=self.client_id,
                client_credential=self.client_credential,
            )
            token = app.acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"])
        except ValueError as exc:
            logger.error("Couldn't set up credentials for OneDrive")
            raise exc
        return token


@dataclass
class OneDriveIngestDoc(IngestDocCleanupMixin, BaseIngestDoc):
    config: SimpleOneDriveConfig
    file: "DriveItem"

    def __post_init__(self):
        self.ext = "".join(Path(self.file.name).suffixes)
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

        if parent_ref := self.file.get_property("parentReference", "").path.split(":")[-1]:
            odir = parent_ref[1:] if parent_ref[0] == "/" else parent_ref
            download_path = download_path if odir == "" else (download_path / odir).resolve()
            output_path = output_path if odir == "" else (output_path / odir).resolve()

        self.download_dir = download_path
        self.download_filepath = (download_path / self.file.name).resolve()
        oname = f"{self.file.name[:-len(self.ext)]}.json"
        self.output_dir = output_path
        self.output_filepath = (output_path / oname).resolve()

    @property
    def filename(self):
        return Path(self.download_filepath).resolve()

    @property
    def _output_filename(self):
        return Path(self.output_filepath).resolve()

    @BaseIngestDoc.skip_if_file_exists
    @requires_dependencies(["office365"])
    def get_file(self):
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
        return


class OneDriveConnector(ConnectorCleanupMixin, BaseConnector):
    config: SimpleOneDriveConfig

    def __init__(self, standard_config: StandardConnectorConfig, config: SimpleOneDriveConfig):
        super().__init__(standard_config, config)
        self._set_client()

    @requires_dependencies(["office365"])
    def _set_client(self):
        from office365.graph_client import GraphClient

        self.client = GraphClient(self.config.token_factory)

    def _list_objects(self, folder, recursive) -> List["DriveItem"]:
        drive_items = folder.children.get().execute_query()
        files = [d for d in drive_items if d.is_file]
        if not recursive:
            return files
        folders = [d for d in drive_items if d.is_folder]
        for f in folders:
            files += self._list_objects(f, recursive)
        return files

    def initialize(self):
        pass

    def get_ingest_docs(self):
        root = self.client.users[self.config.user_pname].drive.get().execute_query().root
        if fpath := self.config.folder:
            root = root.get_by_path(fpath).get().execute_query()
            if root is None or not root.is_folder:
                raise ValueError(f"Unable to find directory, given: {fpath}")
        files = self._list_objects(root, self.config.recursive)
        return [OneDriveIngestDoc(self.standard_config, self.config, f) for f in files]
