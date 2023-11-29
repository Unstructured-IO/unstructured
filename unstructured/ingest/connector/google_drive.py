import io
import json
import os
import typing as t
from dataclasses import dataclass, field
from datetime import datetime
from mimetypes import guess_extension
from pathlib import Path

from unstructured.file_utils.filetype import EXT_TO_FILETYPE
from unstructured.file_utils.google_filetype import GOOGLE_DRIVE_EXPORT_TYPES
from unstructured.ingest.error import SourceConnectionError, SourceConnectionNetworkError
from unstructured.ingest.interfaces import (
    BaseConnectorConfig,
    BaseSessionHandle,
    BaseSingleIngestDoc,
    BaseSourceConnector,
    ConfigSessionHandleMixin,
    IngestDocCleanupMixin,
    IngestDocSessionHandleMixin,
    SourceConnectorCleanupMixin,
    SourceMetadata,
)
from unstructured.ingest.logger import logger
from unstructured.utils import requires_dependencies

if t.TYPE_CHECKING:
    from googleapiclient.discovery import Resource as GoogleAPIResource
    from googleapiclient.http import MediaIoBaseDownload

FILE_FORMAT = "{id}-{name}{ext}"
DIRECTORY_FORMAT = "{id}-{name}"


@dataclass
class GoogleDriveSessionHandle(BaseSessionHandle):
    service: "GoogleAPIResource"


@requires_dependencies(["googleapiclient"], extras="google-drive")
def create_service_account_object(key_path: t.Union[str, dict], id=None):
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
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError

    try:
        if isinstance(key_path, dict):
            creds = service_account.Credentials.from_service_account_info(key_path)
        elif isinstance(key_path, str):
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = key_path
            creds, _ = default()
        else:
            raise ValueError(
                f"key path not recognized as a dictionary or a file path: "
                f"[{type(key_path)}] {key_path}",
            )
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
    service_account_key: t.Union[str, dict]
    extension: t.Optional[str] = None
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
class GoogleDriveIngestDoc(IngestDocSessionHandleMixin, IngestDocCleanupMixin, BaseSingleIngestDoc):
    connector_config: SimpleGoogleDriveConfig
    meta: t.Dict[str, str] = field(default_factory=dict)
    registry_name: str = "google_drive"

    @property
    def filename(self):
        return Path(self.meta.get("download_filepath")).resolve()  # type: ignore

    @property
    def _output_filename(self):
        return Path(f"{self.meta.get('output_filepath')}.json").resolve()

    @property
    def record_locator(self) -> t.Optional[t.Dict[str, t.Any]]:
        return {
            "drive_id": self.connector_config.drive_id,
            "file_id": self.meta["id"],
        }

    @requires_dependencies(["googleapiclient"], extras="google-drive")
    def update_source_metadata(self):
        from googleapiclient.errors import HttpError

        try:
            file_obj = (
                self.session_handle.service.files()
                .get(
                    fileId=self.meta["id"],
                    fields="id, createdTime, modifiedTime, version, webContentLink",
                )
                .execute()
            )
        except HttpError as e:
            if e.status_code == 404:
                logger.error(f"File {self.meta['name']} not found")
                self.source_metadata = SourceMetadata(
                    exists=True,
                )
                return
            raise

        date_created = None
        if dc := file_obj.get("createdTime", ""):
            date_created = datetime.strptime(
                dc,
                "%Y-%m-%dT%H:%M:%S.%fZ",
            ).isoformat()

        date_modified = None
        if dm := file_obj.get("modifiedTime", ""):
            date_modified = datetime.strptime(
                dm,
                "%Y-%m-%dT%H:%M:%S.%fZ",
            ).isoformat()

        self.source_metadata = SourceMetadata(
            date_created=date_created,
            date_modified=date_modified,
            version=file_obj.get("version", ""),
            source_url=file_obj.get("webContentLink", ""),
            exists=True,
        )

    @SourceConnectionNetworkError.wrap
    def _run_downloader(self, downloader: "MediaIoBaseDownload") -> bool:
        downloaded = False
        while downloaded is False:
            _, downloaded = downloader.next_chunk()
        return downloaded

    @requires_dependencies(["googleapiclient"], extras="google-drive")
    @SourceConnectionError.wrap
    @BaseSingleIngestDoc.skip_if_file_exists
    def get_file(self):
        from googleapiclient.http import MediaIoBaseDownload

        if self.meta.get("mimeType", "").startswith("application/vnd.google-apps"):
            export_mime = GOOGLE_DRIVE_EXPORT_TYPES.get(
                self.meta.get("mimeType"),  # type: ignore
            )
            if not export_mime:
                logger.info(
                    f"File not supported. Name: {self.meta.get('name')} "
                    f"ID: {self.meta.get('id')} "
                    f"MimeType: {self.meta.get('mimeType')}",
                )
                return

            request = self.session_handle.service.files().export_media(
                fileId=self.meta.get("id"),
                mimeType=export_mime,
            )
        else:
            request = self.session_handle.service.files().get_media(fileId=self.meta.get("id"))
        file = io.BytesIO()
        downloader = MediaIoBaseDownload(file, request)
        self.update_source_metadata()
        downloaded = self._run_downloader(downloader=downloader)

        saved = False
        if downloaded and file:
            dir_ = Path(self.meta["download_dir"])
            if dir_:
                if not dir_.is_dir():
                    logger.debug(f"Creating directory: {self.meta.get('download_dir')}")

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
            Path(self.processor_config.output_dir),
            recursive,
        )
        return files

    def initialize(self):
        pass

    def check_connection(self):
        try:
            self.connector_config.create_session_handle().service
        except Exception as e:
            logger.error(f"failed to validate connection: {e}", exc_info=True)
            raise SourceConnectionError(f"failed to validate connection: {e}")

    def get_ingest_docs(self):
        files = self._list_objects(self.connector_config.drive_id, self.connector_config.recursive)
        return [
            GoogleDriveIngestDoc(
                connector_config=self.connector_config,
                processor_config=self.processor_config,
                read_config=self.read_config,
                meta=file,
            )
            for file in files
        ]
