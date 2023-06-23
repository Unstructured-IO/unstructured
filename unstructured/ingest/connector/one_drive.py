import os
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING
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


@dataclass
class SimpleOneDriveConfig(BaseConnectorConfig):

    client_id: str
    client_credential: str
    authority_url: str = 'https://login.microsoftonline.com'
    tenant: str = 'common'
    user_pname: str
    recursive: bool = False

    def __post_init__(self):
        if not (self.client_id and self.client_credential and self.user_pname):
            raise ValueError(
                'Please provide one of the following mandatory values:'
                '\n-client_id\n-client_credential\n-user_principal_name'
            )
        self.token_factory = self._acquire_token

    @requires_dependencies(["msal"])
    def _acquire_token(self):
        from msal import ConfidentialClientApplication
        try:
            app = ConfidentialClientApplication(
                authority=self.authority_url,
                client_id=self.client_id,
                client_credential=self.client_credential)
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
        self.fname = self.file.name
        self.fpath = self.file.get_property('parentReference','').split(':')[-1]

    @property
    def filename(self):
        pass

    def _output_filename(self):
        pass

    def cleanup_file(self):
        pass

    def has_output(self) -> bool:
        pass

    def get_file(self):
        pass

    def write_result(self):
        pass

class OneDriveConnector(BaseConnector):

    config: SimpleOneDriveConfig

    def __init__(self, standard_config: StandardConnectorConfig, config: SimpleOneDriveConfig):
        super().__init__(standard_config, config)
        self.cleanup_files = (
            not self.standard_config.preserve_downloads and not self.standard_config.download_only
        )
        self.client = self._set_client

    @requires_dependencies(['office365'])
    def _set_client(self):
        from office365.graph_client import GraphClient
        return GraphClient(self.config.token_factory)
    
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
        