from dataclasses import dataclass, field
from mimetypes import guess_extension
from pathlib import Path
import json
import io
import os
import re

from google.auth import exceptions
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload

from unstructured.ingest.interfaces import BaseConnector, BaseConnectorConfig, BaseIngestDoc

FILE_FORMAT = "{id}-{name}{ext}"
DIRECTORY_FORMAT = "{id}-{name}"


@dataclass
class SimpleGoogleDriveConfig(BaseConnectorConfig):
    """Connector config where s3_url is an s3 prefix to process all documents from."""
    # Google Drive Specific Options
    drive_id: str
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
        try:
            self.service = build("drive", "v3", developerKey=self.api_key)
            response = self.service.files().list(spaces="drive", fields="files(id)", pageToken=None,
                                                 corpora="user", q=f"'{self.drive_id}' in parents").execute()
        except HttpError as exc:
            raise ValueError(f"{exc.reason}")
        except exceptions.DefaultCredentialsError:
            raise ValueError("The provided API key is invalid.")


@dataclass
class GoogleDriveIngestDoc(BaseIngestDoc):
    config: SimpleGoogleDriveConfig
    file_meta: dict

    @property
    def filename(self):
        return (Path(self.file_meta.get("download_filepath"))).resolve()

    def _output_filename(self):
        return Path(f"{self.filename}.json").resolve()

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
        if not self.config.re_download and self.filename.is_file() and self.filename.stat():
            if self.config.verbose:
                print(f"File exists: {self.filename}, skipping download")
            return

        request = self.config.service.files().get_media(fileId=self.file_meta.get("id"))
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
        self.files = self._list_objects(self.config.drive_id)

    def _list_objects(self, folder_id, recursive=False):
        files = []

        def traverse(download_dir, folder_id, recursive=False):
            page_token = None
            while True:
                response = self.config.service.files().list(
                    spaces='drive', fields='nextPageToken, files(id, name, mimeType)',
                    pageToken=page_token, corpora="user", q=f"'{folder_id}' in parents").execute()

                for meta in response.get("files", []):
                    if meta.get("mimeType") == "application/vnd.google-apps.folder":
                        dir_ = DIRECTORY_FORMAT.format(name=meta.get("name"), id=meta.get("id"))
                        if recursive:
                            sub_dir = (download_dir / dir_).resolve()
                            meta["files"] = traverse(sub_dir, meta.get("id"), True)
                    else:
                        # TODO (Habeeb) Extract extension from file
                        ext = guess_extension(meta.get("mimeType"))
                        name = FILE_FORMAT.format(name=meta.get("name"), id=meta.get("id"), ext=ext)
                        meta["download_dir"] = download_dir
                        meta["download_filepath"] = (download_dir / name).resolve()
                    files.append(meta)

                page_token = response.get('nextPageToken', None)
                if page_token is None:
                    break

        traverse(Path(self.config.download_dir), folder_id, recursive)

        return files

    def cleanup(self, cur_dir=None):
        if not self.cleanup_files:
            return

        if cur_dir is None:
            cur_dir = self.config.download_dir
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
        Path(self.config.download_dir).mkdir(parents=True, exist_ok=True)
        for file in self.files:
            if file.get("mimeType") == "application/vnd.google-apps.folder":
                Path(file.get("download_filepath")).mkdir(parents=True, exist_ok=True)

    def get_ingest_docs(self):
        return [
            GoogleDriveIngestDoc(self.config, file)
            for file in self.files
        ]
