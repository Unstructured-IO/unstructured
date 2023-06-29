import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from unstructured.file_utils.filetype import EXT_TO_FILETYPE
from unstructured.ingest.interfaces import (
    BaseConnector,
    BaseConnectorConfig,
    BaseIngestDoc,
    StandardConnectorConfig,
)
from unstructured.ingest.logger import logger
from unstructured.utils import requires_dependencies

if TYPE_CHECKING:
    from office365.onedrive.driveitems import driveItem


MAX_MB_SIZE = 512_000_000


@dataclass
class SimpleOneDriveConfig(BaseConnectorConfig):
    client_id: str
    client_credential: str = field(repr=False)
    user_pname: str
    tenant: str = field(repr=False)
    authority_url: str = field(repr=False)
    recursive: bool = False

    def __post_init__(self):
        if not (self.client_id and self.client_credential and self.user_pname):
            raise ValueError(
                "Please provide one of the following mandatory values:"
                "\n-client_id\n-client_credential\n-user_principal_name",
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
class OneDriveIngestDoc(BaseIngestDoc):
    config: SimpleOneDriveConfig
    file: "driveItem"

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
        """Sets download and output directories"""
        dpath = Path(f"{self.standard_config.download_dir}")
        opath = Path(f"{self.standard_config.output_dir}")

        if pref := self.file.get_property("parentReference", "").path.split(":")[-1]:
            odir = pref[1:] if pref[0] == "/" else pref
            dpath = dpath if odir == "" else (dpath / odir).resolve()
            opath = opath if odir == "" else (opath / odir).resolve()

        dname = f'{self.file.get_property("id")}-{self.file.name}'
        self.download_dir = dpath
        self.download_filepath = (dpath / dname).resolve()
        oname = f"{dname[:-len(self.ext)]}.json"
        self.output_dir = opath
        self.output_filepath = (opath / oname).resolve()

    @property
    def filename(self):
        return Path(self.download_filepath).resolve()

    def _output_filename(self):
        return Path(self.output_filepath).resolve()

    def cleanup_file(self):
        if (
            not self.standard_config.preserve_downloads
            and self.filename.is_file()
            and not self.standard_config.download_only
        ):
            logger.debug(f"Cleaning up {self}")
            Path.unlink(self.filename)

    def has_output(self) -> bool:
        """Determine if structured output for this doc already exists."""
        return self._output_filename().is_file() and self._output_filename().stat()

    @requires_dependencies(["office365"])
    def get_file(self):
        if (
            not self.standard_config.re_download
            and self.filename.is_file()
            and self.filename.stat()
        ):
            logger.debug(f"File exists: {self.filename}, skipping download")
            return

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

    def write_result(self):
        """Write the structured json result for this doc. result must be json serializable."""

        if self.standard_config.download_only:
            return
        output_filename = self._output_filename()
        output_filename.parent.mkdir(parents=True, exist_ok=True)

        if not self.output_dir.is_dir():
            logger.debug(f"Creating directory: {self.output_dir}")
            self.output_dir.mkdir(parents=True, exist_ok=True)

        with output_filename.open(mode="w") as output_f:
            output_f.write(json.dumps(self.isd_elems_no_filename[0], ensure_ascii=False, indent=2))
        logger.info(f"Wrote {output_filename}")


class OneDriveConnector(BaseConnector):
    config: SimpleOneDriveConfig

    def __init__(self, standard_config: StandardConnectorConfig, config: SimpleOneDriveConfig):
        super().__init__(standard_config, config)
        self.cleanup_files = (
            not self.standard_config.preserve_downloads and not self.standard_config.download_only
        )
        self._set_client()

    @requires_dependencies(["office365"])
    def _set_client(self):
        from office365.graph_client import GraphClient

        self.client = GraphClient(self.config.token_factory)

    def _list_objects(self, folder, recursive) -> list:
        drive_items = folder.children.get().execute_query()
        files = [d for d in drive_items if d.is_file]
        if not recursive:
            return files
        folders = [d for d in drive_items if d.is_folder]
        for f in folders:
            files += self._list_objects(f, recursive)
        return files

    def cleanup(self, cur_dir=None):
        if not self.cleanup_files:
            return

        if cur_dir is None:
            cur_dir = self.standard_config.download_dir
        sub_dirs = os.listdir(cur_dir)
        os.chdir(cur_dir)
        for sub_dir in sub_dirs:
            # don't traverse symlinks, not that there every should be any
            if os.path.isdir(sub_dir) and not os.path.islink(sub_dir):
                self.cleanup(sub_dir)
        os.chdir("..")
        if len(os.listdir(cur_dir)) == 0:
            os.rmdir(cur_dir)

    def initialize(self):
        pass

    def get_ingest_docs(self):
        drive = self.client.users[self.config.user_pname].drive.get().execute_query()
        files = self._list_objects(drive.root, self.config.recursive)
        return [OneDriveIngestDoc(self.standard_config, self.config, f) for f in files]
