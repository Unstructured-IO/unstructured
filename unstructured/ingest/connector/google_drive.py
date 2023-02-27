from dataclasses import dataclass, field
from pathlib import Path
import json
import io
import os
import re

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload

from unstructured.ingest.interfaces import BaseConnector, BaseConnectorConfig, BaseIngestDoc

FILE_FORMAT = "{id}-{name}"


@dataclass
class SimpleGoogleDriveConfig(BaseConnectorConfig):
    """Connector config where s3_url is an s3 prefix to process all documents from."""

    # Google Drive Specific Options
    folder_id: str
    api_key: str
    # TODO (HAKSOAT) Add auth id
    # TODO (HAKSOAT) Allow download without id (has limitations)

    # Standard Connector options
    download_dir: str
    # where to write structured data, with the directory structure matching s3 path
    output_dir: str
    re_download: bool = False
    preserve_downloads: bool = False
    # if a structured output .json file already exists, do not reprocess an s3 file to overwrite it
    reprocess: bool = False
    verbose: bool = False

    recursive: bool = False

    def __post_init__(self):
        self.service = build("drive", "v3", self.api_key)

        # just a bucket with no trailing prefix
        try:
            response = self.service.files().list(spaces="drive", fields="files(id)", page_token=None,
                                            corpora="user", q=f"'{self.folder_id}' in parents").execute()
        except HttpError:
            pass


@dataclass
class GoogleDriveIngestDoc(BaseIngestDoc):
    config: SimpleGoogleDriveConfig
    file_id: str

    @property
    def filename(self):
        return (Path(self.config.download_dir) / self.file_id).resolve()

    def cleanup_file(self):
        if not self.config.preserve_downloads:
            if self.config.verbose:
                print(f"cleaning up {self}")
            Path.unlink(self.filename)

    def has_output(self):
        """Determine if structured output for this doc already exists."""
        output_filename = self._output_filename()
        return output_filename.is_file() and output_filename.stat()

    def get_file(self):
        # TODO: Add verbose logs
        request = self.config.service.files().get_media(fileId=self.file_id)
        file = io.BytesIO()
        downloader = MediaIoBaseDownload(file, request)
        done = False
        while done is False:
            status, done = downloader.next_chunk()

        if file:
            with open(self.filename, "wb") as handler:
                handler.write(file.getbuffer())

    def write_result(self):
        """Write the structured json result for this doc. result must be json serializable."""
        output_filename = self._output_filename()
        output_filename.parent.mkdir(parents=True, exist_ok=True)
        with open(output_filename, "w") as output_f:
            output_f.write(json.dumps(self.isd_elems_no_filename, ensure_ascii=False, indent=2))
        print(f"Wrote {output_filename}")


class GoogleDriveConnector(BaseConnector):
    """Objects of this class support fetching documents from Google Drive"""
    def __init__(self, config):
        self.config = config
        self.files = []

    def traverse(self, folder_id, recursive=False):
        page_token = None
        files = []

        while True:
            response = self.config.service.files().list(
                spaces='drive', fields='nextPageToken, files(id, name, mimeType)',
                pageToken=page_token, corpora="user", q=f"'{folder_id}' in parents").execute()

            for file in response.get("files", []):
                if file.get("mimeType") == "application/vnd.google-apps.folder":
                    if recursive:
                        file["files"] = self.traverse(file.get("id"), True)

            files.extend(response.get('files', []))
            page_token = response.get('nextPageToken', None)
            if page_token is None:
                break

        return files

    def cleanup(self, cur_dir=None):
        pass

    def initialize(self):
        self.files = self.traverse(self.config.folder_id)

        def recursive_mkdir(files):
            for file in files:
                if file.get("mimeType") == "application/vnd.google-apps.folder":
                    name = FILE_FORMAT.format(name=file.get("name"), id=file.get("id"))
                    sub_dir = (Path(self.config.download_dir) / name).resolve()
                    sub_dir.mkdir(parents=True, exist_ok=True)
                    # TODO: (HAKSOAT) What are the chances we have cyclic directories due to shortcuts?
                    recursive_mkdir(file.get("files", []))

    def _list_objects(self):
        pass

    def get_ingest_docs(self):
        pass