import os
import hashlib
from collections import defaultdict
from pathlib import Path
from typing import List
from dataclasses import dataclass, field
from itertools import chain

from office365.onedrive.driveitems.driveItem import DriveItem

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

MAX_NUM_EMAILS = 10000

class MissingFolderError(Exception):
    """There are no root folders with those names. """

@dataclass
class SimpleOutlookConfig(BaseConnectorConfig):
    """This class is getting the token."""

    client_id: str
    client_credential: str = field(repr=False)
    user_pname: str
    tenant: str = field(repr=False)
    authority_url: str = field(repr=False)
    ms_outlook_folders: List[str]
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
            token = app.acquire_token_for_client(
                scopes=["https://graph.microsoft.com/.default"]
            )
        except ValueError as exc:
            logger.error("Couldn't set up credentials for Outlook")
            raise exc
        return token

    @staticmethod
    def parse_channels(channel_str: str) -> List[str]:
        """Parses a comma separated list of channels into a list."""
        return [x.strip() for x in channel_str.split(",")]


@dataclass
class OutlookIngestDoc(IngestDocCleanupMixin, BaseIngestDoc):
    config: SimpleOutlookConfig
    file: DriveItem

    def __post_init__(self):
        self._set_download_paths()

    def hash_mail_name(self, id):
        """Outlook email ids are 152 char long. Hash to shorten."""
        return hashlib.sha256(id.encode("utf-8")).hexdigest()[:16]

    def _set_download_paths(self) -> None:
        """Parses the folder structure from the source and creates the download and output paths"""
        download_path = Path(f"{self.standard_config.download_dir}")
        output_path = Path(f"{self.standard_config.output_dir}")

        self.download_dir = download_path
        self.download_filepath = (
            download_path / f"{self.hash_mail_name(self.file.id)}.eml"
        ).resolve()
        oname = f"{self.hash_mail_name(self.file.id)}.eml.json"
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
            if not self.download_dir.is_dir():
                logger.debug(f"Creating directory: {self.download_dir}")
                self.download_dir.mkdir(parents=True, exist_ok=True)

            with open(
                os.path.join(
                    self.download_dir, self.hash_mail_name(self.file.id) + ".eml"
                ),
                "wb",
            ) as local_file:
                self.file.download(
                    local_file
                ).execute_query()  # download MIME representation of a message

        except Exception as e:
            logger.error(
                f"Error while downloading and saving file: {self.file.subject}."
            )
            logger.error(e)
            return
        logger.info(f"File downloaded: {self.file.subject}")
        return


class OutlookConnector(ConnectorCleanupMixin, BaseConnector):
    config: SimpleOutlookConfig

    def __init__(
        self, standard_config: StandardConnectorConfig, config: SimpleOutlookConfig
    ):
        super().__init__(standard_config, config)
        self._set_client()
        self.get_folder_ids()

    @requires_dependencies(["office365"])
    def _set_client(self):
        from office365.graph_client import GraphClient

        self.client = GraphClient(self.config.token_factory)

    def initialize(self):
        pass

    def recurse_folders(self, folder_id, main_folder_dict):
        subfolders = (
            self.client.users[self.config.user_pname]
            .mail_folders[folder_id]
            .child_folders.get()
            .execute_query()
        )
        for subfolder in subfolders:
            for k, v in main_folder_dict.items():
                if subfolder.get_property("parentFolderId") in v:
                    v.append(subfolder.id)
            if subfolder.get_property("childFolderCount") > 0:
                self.recurse_folders(subfolder.id, main_folder_dict)

    def get_folder_ids(self):
        self.root_folders = defaultdict(list)
        root_folders_with_subfolders = []
        root_folders = (
            self.client.users[self.config.user_pname].mail_folders.get().execute_query()
        )

        for folder in root_folders:
            self.root_folders[folder.display_name].append(folder.id)
            if folder.get_property("childFolderCount") > 0:
                root_folders_with_subfolders.append(folder.id)

        for folder in root_folders_with_subfolders:
            self.recurse_folders(folder, self.root_folders)

        self.selected_folder_ids = list(
            chain.from_iterable(
                [
                    v
                    for k, v in self.root_folders.items()
                    if k.lower() in [x.lower() for x in self.config.ms_outlook_folders]
                ]
            )
        )
        if not self.selected_folder_ids:
            raise MissingFolderError(
                f"There are no root folders with the names: {self.config.ms_outlook_folders}",
            )

    def get_ingest_docs(self):
        mail = (
            self.client.users[self.config.user_pname]
            .messages.get()
            .top(MAX_NUM_EMAILS)
            .execute_query()
        )
        filtered_mail = [
            m for m in mail if m.parent_folder_id in self.selected_folder_ids
        ]

        return [
            OutlookIngestDoc(self.standard_config, self.config, f)
            for f in filtered_mail
        ]
