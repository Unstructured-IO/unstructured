import io
import json
import os
import typing as t
from dataclasses import dataclass
from mimetypes import guess_extension
from pathlib import Path

from unstructured.file_utils.filetype import EXT_TO_FILETYPE
from unstructured.file_utils.google_filetype import GOOGLE_DRIVE_EXPORT_TYPES
from unstructured.ingest.error import SourceConnectionError
from unstructured.ingest.interfaces import (
    BaseConnectorConfig,
    BaseIngestDoc,
    BaseSessionHandle,
    BaseSourceConnector,
    ConfigSessionHandleMixin,
    IngestDocCleanupMixin,
    IngestDocSessionHandleMixin,
    SourceConnectorCleanupMixin,
)
from unstructured.ingest.logger import logger
from unstructured.utils import requires_dependencies

if t.TYPE_CHECKING:
    from googleapiclient.discovery import Resource as GoogleAPIResource

FILE_FORMAT = "{id}-{name}{ext}"
DIRECTORY_FORMAT = "{id}-{name}"


@dataclass
class GoogleDriveSessionHandle(BaseSessionHandle):
    service: "GoogleAPIResource"


@requires_dependencies(["googleapiclient"], extras="google-drive")
def create_service_account_object(key_path, id=None):
    """
    Creates a service object for interacting with Google Drive.

    Providing a drive id enforces a key validation process.

    Args:
        key_path: Path to Google Drive service account json file.
        id: ID of a file on Google Drive. File has to be either publicly accessible or accessible
            to the service account.

    Returns:
        Service account object
    """
    from google.auth import default, exceptions
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError

    try:
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = key_path
        creds, _ = default()
        service = build("drive", "v3", credentials=creds)

        if id:
            service.files().list(
                spaces="drive",
                fields="files(id)",
                pageToken=None,
                corpora="user",
                q=f"'{id}' in parents",
            ).execute()

    except HttpError as exc:
        raise ValueError(f"{exc.reason}")
    except exceptions.DefaultCredentialsError:
        raise ValueError("The provided API key is invalid.")

    return service


@dataclass
class SimpleGoogleDriveConfig(ConfigSessionHandleMixin, BaseConnectorConfig):
    """Connector config where drive_id is the id of the document to process or
    the folder to process all documents from."""

    # Google Drive Specific Options
    drive_id: str
    service_account_key: str
    extension: t.Optional[str]
    recursive: bool = False

    def __post_init__(self):
        if self.extension and self.extension not in EXT_TO_FILETYPE:
            raise ValueError(
                f"Extension not supported. "
                f"Value MUST be one of {', '.join([k for k in EXT_TO_FILETYPE if k is not None])}.",
            )

    def create_session_handle(
        self,
    ) -> GoogleDriveSessionHandle:
        service = create_service_account_object(self.service_account_key)
        return GoogleDriveSessionHandle(service=service)


@dataclass
class GoogleDriveIngestDoc(IngestDocSessionHandleMixin, IngestDocCleanupMixin, BaseIngestDoc):
    connector_config: SimpleGoogleDriveConfig
    file_meta: t.Dict[str, str]
    registry_name: str = "google_drive"

    @property
    def filename(self):
        return Path(self.file_meta.get("download_filepath")).resolve()  # type: ignore

    @property
    def _output_filename(self):
        return Path(f"{self.file_meta.get('output_filepath')}.json").resolve()

    @SourceConnectionError.wrap
    @BaseIngestDoc.skip_if_file_exists
    @requires_dependencies(["googleapiclient"], extras="google-drive")
    def get_file(self):
        from googleapiclient.errors import HttpError
        from googleapiclient.http import MediaIoBaseDownload

        if self.file_meta.get("mimeType", "").startswith("application/vnd.google-apps"):
            export_mime = GOOGLE_DRIVE_EXPORT_TYPES.get(
                self.file_meta.get("mimeType"),  # type: ignore
            )
            if not export_mime:
                logger.info(
                    f"File not supported. Name: {self.file_meta.get('name')} "
                    f"ID: {self.file_meta.get('id')} "
                    f"MimeType: {self.file_meta.get('mimeType')}",
                )
                return

            request = self.session_handle.service.files().export_media(
                fileId=self.file_meta.get("id"),
                mimeType=export_mime,
            )
        else:
            request = self.session_handle.service.files().get_media(fileId=self.file_meta.get("id"))
        file = io.BytesIO()
        downloader = MediaIoBaseDownload(file, request)
        downloaded = False
        try:
            while downloaded is False:
                status, downloaded = downloader.next_chunk()
        except HttpError:
            pass

        saved = False
        if downloaded and file:
            dir_ = Path(self.file_meta["download_dir"])
            if dir_:
                if not dir_.is_dir():
                    logger.debug(f"Creating directory: {self.file_meta.get('download_dir')}")

                    if dir_:
                        dir_.mkdir(parents=True, exist_ok=True)

                with open(self.filename, "wb") as handler:
                    handler.write(file.getbuffer())
                    saved = True
                    logger.debug(f"File downloaded: {self.filename}.")

        if not saved:
            logger.error(f"Error while downloading and saving file: {self.filename}.")

    def write_result(self):
        """Write the structured json result for this doc. result must be json serializable."""
        if self.read_config.download_only:
            return
        self._output_filename.parent.mkdir(parents=True, exist_ok=True)
        with open(self._output_filename, "w") as output_f:
            output_f.write(json.dumps(self.isd_elems_no_filename, ensure_ascii=False, indent=2))
        logger.info(f"Wrote {self._output_filename}")


@dataclass
class GoogleDriveSourceConnector(SourceConnectorCleanupMixin, BaseSourceConnector):
    """Objects of this class support fetching documents from Google Drive"""

    connector_config: SimpleGoogleDriveConfig

    def _list_objects(self, drive_id, recursive=False):
        files = []
        service = self.connector_config.create_session_handle().service

        def traverse(drive_id, download_dir, output_dir, recursive=False):
            page_token = None
            while True:
                response = (
                    service.files()
                    .list(
                        spaces="drive",
                        fields="nextPageToken, files(id, name, mimeType)",
                        pageToken=page_token,
                        corpora="user",
                        q=f"'{drive_id}' in parents",
                    )
                    .execute()
                )

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
                                logger.info(
                                    f"File {meta.get('name')} has an "
                                    f"unsupported MimeType {meta.get('mimeType')}",
                                )
                                continue

                            if not ext:
                                guess = guess_extension(export_mime)
                                ext = guess if guess else ext

                        # TODO (Habeeb): Consider filtering at the query level.
                        if (
                            self.connector_config.extension
                            and self.connector_config.extension != ext
                        ):  # noqa: SIM102
                            logger.debug(
                                f"File {meta.get('name')} does not match "
                                f"the file type {self.connector_config.extension}",
                            )
                            continue

                        name = FILE_FORMAT.format(name=meta.get("name"), id=meta.get("id"), ext=ext)
                        meta["download_dir"] = str(download_dir)
                        meta["download_filepath"] = (download_dir / name).resolve().as_posix()
                        meta["output_dir"] = str(output_dir)
                        meta["output_filepath"] = (output_dir / name).resolve().as_posix()
                        files.append(meta)

                page_token = response.get("nextPageToken", None)
                if page_token is None:
                    break

        traverse(
            drive_id,
            Path(self.read_config.download_dir),
            Path(self.partition_config.output_dir),
            recursive,
        )
        return files

    def initialize(self):
        pass

    def get_ingest_docs(self):
        files = self._list_objects(self.connector_config.drive_id, self.connector_config.recursive)
        return [
            GoogleDriveIngestDoc(
                connector_config=self.connector_config,
                partition_config=self.partition_config,
                read_config=self.read_config,
                file_meta=file,
            )
            for file in files
        ]
