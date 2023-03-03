from dataclasses import dataclass, field
from mimetypes import guess_extension
from pathlib import Path
import json
import io
import os
import re

from unstructured.ingest.interfaces import BaseConnector, BaseConnectorConfig, BaseIngestDoc
from unstructured.file_utils.filetype import EXT_TO_FILETYPE
from unstructured.file_utils.google_filetype import GOOGLE_DRIVE_EXPORT_TYPES
from unstructured.utils import requires_dependencies


FILE_FORMAT = "{id}-{name}{ext}"
DIRECTORY_FORMAT = "{id}-{name}"


@dataclass
class SimpleGoogleDriveConfig(BaseConnectorConfig):
    """Connector config where s3_url is an s3 prefix to process all documents from."""
    # Google Drive Specific Options
    drive_id: str
    api_key: str
    extension: str
    # TODO (HAKSOAT) Add auth id
    # TODO (HAKSOAT) Allow download without id (has limitations)

    # Standard Connector options
    download_dir: str
    # where to write structured data, with the directory structure matching drive path
    output_dir: str
    re_download: bool = False
    preserve_downloads: bool = False
    verbose: bool = False

    recursive: bool = False

    @requires_dependencies(["googleapiclient"], extras="google-drive")
    def __post_init__(self):
        from google.auth import exceptions
        from googleapiclient.discovery import build
        from googleapiclient.errors import HttpError

        if self.extension and self.extension not in EXT_TO_FILETYPE.keys():
            raise ValueError(f"Extension not supported. Value MUST be one of {', '.join(EXT_TO_FILETYPE.keys())}.")

        try:
            self.service = build("drive", "v3", developerKey=self.api_key)
            self.service.files().list(spaces="drive", fields="files(id)", pageToken=None,
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
        return Path(self.file_meta.get("download_filepath")).resolve()

    def _output_filename(self):
        return Path(f"{self.file_meta.get('output_filepath')}.json").resolve()

    def cleanup_file(self):
        if not self.config.preserve_downloads and self.filename.is_file():
            if self.config.verbose:
                print(f"cleaning up {self}")
            Path.unlink(self.filename)

    def has_output(self):
        """Determine if structured output for this doc already exists."""
        output_filename = self._output_filename()
        return output_filename.is_file() and output_filename.stat()

    @requires_dependencies(["googleapiclient"], extras="google-drive")
    def get_file(self):
        from googleapiclient.http import MediaIoBaseDownload

        if not self.config.re_download and self.filename.is_file() and self.filename.stat():
            if self.config.verbose:
                print(f"File exists: {self.filename}, skipping download")
            return

        if self.file_meta.get("mimeType", "").startswith("application/vnd.google-apps"):
            export_mime = GOOGLE_DRIVE_EXPORT_TYPES.get(self.file_meta.get("mimeType"))
            if not export_mime:
                print(f"File not supported. Name: {self.file_meta.get('name')} "
                      f"ID: {self.file_meta.get('id')} "
                      f"MimeType: {self.file_meta.get('mimeType')}")
                return

            request = self.config.service.files().export_media(
                fileId=self.file_meta.get("id"), mimeType=export_mime)
        else:
            request = self.config.service.files().get_media(fileId=self.file_meta.get("id"))
        file = io.BytesIO()
        downloader = MediaIoBaseDownload(file, request)
        done = False
        while done is False:
            status, done = downloader.next_chunk()

        if file:
            if not self.file_meta.get("download_dir").is_dir():
                if self.config.verbose:
                    print(f"Creating directory: {self.file_meta.get('download_dir')}")

                self.file_meta.get("download_dir").mkdir(parents=True, exist_ok=True)

            with open(self.filename, "wb") as handler:
                handler.write(file.getbuffer())
                if self.config.verbose:
                    print(f"File downloaded: {self.filename}.")

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
        self.cleanup_files = not self.config.preserve_downloads

    def _list_objects(self, drive_id, recursive=False):
        files = []

        def traverse(drive_id, download_dir, output_dir, recursive=False):
            page_token = None
            while True:
                response = self.config.service.files().list(
                    spaces='drive', fields='nextPageToken, files(id, name, mimeType)',
                    pageToken=page_token, corpora="user", q=f"'{drive_id}' in parents").execute()

                for meta in response.get("files", []):
                    if meta.get("mimeType") == "application/vnd.google-apps.folder":
                        dir_ = DIRECTORY_FORMAT.format(name=meta.get("name"), id=meta.get("id"))
                        if recursive:
                            download_sub_dir = (download_dir / dir_).resolve()
                            output_sub_dir = (output_dir / dir_).resolve()
                            traverse(meta.get("id"), download_sub_dir, output_sub_dir, True)
                    else:
                        ext = ""
                        if not Path(meta.get("name")).suffixes:
                            guess = guess_extension(meta.get("mimeType"))
                            ext = guess if guess else ext

                        if meta.get("mimeType", "").startswith("application/vnd.google-apps"):
                            export_mime = GOOGLE_DRIVE_EXPORT_TYPES.get(meta.get("mimeType"))
                            if not export_mime:
                                continue

                            if not ext:
                                guess = guess_extension(export_mime)
                                ext = guess if guess else ext

                        # TODO (Habeeb): Consider filtering at the query level.
                        if self.config.extension and self.config.extension != ext:
                            continue

                        name = FILE_FORMAT.format(name=meta.get("name"), id=meta.get("id"), ext=ext)
                        meta["download_dir"] = download_dir
                        meta["download_filepath"] = (download_dir / name).resolve()
                        meta["output_dir"] = output_dir
                        meta["output_filepath"] = (output_dir / name).resolve()
                        files.append(meta)

                page_token = response.get('nextPageToken', None)
                if page_token is None:
                    break

        traverse(drive_id, Path(self.config.download_dir), Path(self.config.output_dir), recursive)
        return files

    def cleanup(self, cur_dir=None):
        if not self.cleanup_files:
            return

        if cur_dir is None:
            cur_dir = self.config.download_dir

        if cur_dir is None or not Path(cur_dir).is_dir():
            return

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
        files = self._list_objects(self.config.drive_id, self.config.recursive)
        return [
            GoogleDriveIngestDoc(self.config, file)
            for file in files
        ]
