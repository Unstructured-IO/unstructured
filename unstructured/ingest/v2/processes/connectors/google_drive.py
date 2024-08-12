import io
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, Generator, Optional, Union

from dateutil import parser

from unstructured.documents.elements import DataSourceMetadata
from unstructured.file_utils.google_filetype import GOOGLE_DRIVE_EXPORT_TYPES
from unstructured.ingest.enhanced_dataclass import enhanced_field
from unstructured.ingest.error import SourceConnectionNetworkError
from unstructured.ingest.utils.string_and_date_utils import json_to_dict
from unstructured.ingest.v2.interfaces import (
    AccessConfig,
    ConnectionConfig,
    Downloader,
    DownloaderConfig,
    FileData,
    Indexer,
    IndexerConfig,
    SourceIdentifiers,
    download_responses,
)
from unstructured.ingest.v2.logger import logger
from unstructured.ingest.v2.processes.connector_registry import (
    SourceRegistryEntry,
)
from unstructured.utils import requires_dependencies

CONNECTOR_TYPE = "google_drive"

if TYPE_CHECKING:
    from googleapiclient.discovery import Resource as GoogleAPIResource
    from googleapiclient.http import MediaIoBaseDownload


@dataclass
class GoogleDriveAccessConfig(AccessConfig):
    service_account_key: Union[str, dict]


@dataclass
class GoogleDriveConnectionConfig(ConnectionConfig):
    drive_id: str
    access_config: GoogleDriveAccessConfig = enhanced_field(sensitive=True)

    @requires_dependencies(["googleapiclient"], extras="google-drive")
    def get_files_service(self) -> "GoogleAPIResource":
        from google.auth import default, exceptions
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
        from googleapiclient.errors import HttpError

        # Service account key can be a dict or a file path(str)
        # But the dict may come in as a string
        if isinstance(self.access_config.service_account_key, str):
            key_path = json_to_dict(self.access_config.service_account_key)
        elif isinstance(self.access_config.service_account_key, dict):
            key_path = self.access_config.service_account_key
        else:
            raise TypeError(
                f"access_config.service_account_key must be "
                f"str or dict, got: {type(self.access_config.service_account_key)}"
            )

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
            return service.files()

        except HttpError as exc:
            raise ValueError(f"{exc.reason}")
        except exceptions.DefaultCredentialsError:
            raise ValueError("The provided API key is invalid.")


@dataclass
class GoogleDriveIndexerConfig(IndexerConfig):
    extensions: Optional[list[str]] = None
    recursive: bool = False

    def __post_init__(self):
        # Strip leading period of extension
        if self.extensions is not None:
            self.extensions = [e[1:] if e.startswith(".") else e for e in self.extensions]


@dataclass
class GoogleDriveIndexer(Indexer):
    connection_config: GoogleDriveConnectionConfig
    index_config: GoogleDriveIndexerConfig
    fields: list[str] = field(
        default_factory=lambda: [
            "id",
            "name",
            "mimeType",
            "fileExtension",
            "md5Checksum",
            "sha1Checksum",
            "sha256Checksum",
            "headRevisionId",
            "permissions",
            "createdTime",
            "modifiedTime",
            "version",
            "originalFilename",
            "capabilities",
            "permissionIds",
            "webViewLink",
            "webContentLink",
        ]
    )

    @staticmethod
    def is_dir(record: dict) -> bool:
        return record.get("mimeType") == "application/vnd.google-apps.folder"

    @staticmethod
    def map_file_data(f: dict) -> FileData:
        file_id = f["id"]
        filename = f.pop("name")
        url = f.pop("webContentLink", None)
        version = f.pop("version", None)
        permissions = f.pop("permissions", None)
        date_created_str = f.pop("createdTime", None)
        date_created_dt = parser.parse(date_created_str) if date_created_str else None
        date_modified_str = f.pop("modifiedTime", None)
        parent_path = f.pop("parent_path", None)
        parent_root_path = f.pop("parent_root_path", None)
        date_modified_dt = parser.parse(date_modified_str) if date_modified_str else None
        if (
            parent_path
            and isinstance(parent_path, str)
            and parent_root_path
            and isinstance(parent_root_path, str)
        ):
            fullpath = f"{parent_path}/{filename}"
            rel_path = fullpath.replace(parent_root_path, "")
            source_identifiers = SourceIdentifiers(
                filename=filename, fullpath=fullpath, rel_path=rel_path
            )
        else:
            source_identifiers = SourceIdentifiers(fullpath=filename, filename=filename)
        return FileData(
            connector_type=CONNECTOR_TYPE,
            identifier=file_id,
            source_identifiers=source_identifiers,
            metadata=DataSourceMetadata(
                url=url,
                version=version,
                date_created=str(date_created_dt.timestamp()),
                date_modified=str(date_modified_dt.timestamp()),
                permissions_data=permissions,
                record_locator={
                    "file_id": file_id,
                },
            ),
            additional_metadata=f,
        )

    def get_paginated_results(
        self,
        files_client,
        object_id: str,
        extensions: Optional[list[str]] = None,
        recursive: bool = False,
        previous_path: Optional[str] = None,
    ) -> list[dict]:

        fields_input = "nextPageToken, files({})".format(",".join(self.fields))
        q = f"'{object_id}' in parents"
        # Filter by extension but still include any directories
        if extensions:
            ext_filter = " or ".join([f"fileExtension = '{e}'" for e in extensions])
            q = f"{q} and ({ext_filter} or mimeType = 'application/vnd.google-apps.folder')"
        logger.debug(f"Query used when indexing: {q}")
        logger.debug("response fields limited to: {}".format(", ".join(self.fields)))
        done = False
        page_token = None
        files_response = []
        while not done:
            response: dict = files_client.list(
                spaces="drive",
                fields=fields_input,
                corpora="user",
                pageToken=page_token,
                q=q,
            ).execute()
            if files := response.get("files", []):
                fs = [f for f in files if not self.is_dir(record=f)]
                for r in fs:
                    r["parent_path"] = previous_path
                dirs = [f for f in files if self.is_dir(record=f)]
                files_response.extend(fs)
                if recursive:
                    for d in dirs:
                        dir_id = d["id"]
                        dir_name = d["name"]
                        files_response.extend(
                            self.get_paginated_results(
                                files_client=files_client,
                                object_id=dir_id,
                                extensions=extensions,
                                recursive=recursive,
                                previous_path=f"{previous_path}/{dir_name}",
                            )
                        )
            page_token = response.get("nextPageToken")
            if page_token is None:
                done = True
        for r in files_response:
            r["parent_root_path"] = previous_path
        return files_response

    def get_root_info(self, files_client, object_id: str) -> dict:
        return files_client.get(fileId=object_id, fields=",".join(self.fields)).execute()

    def get_files(
        self,
        files_client,
        object_id: str,
        recursive: bool = False,
        extensions: Optional[list[str]] = None,
    ) -> list[FileData]:
        root_info = self.get_root_info(files_client=files_client, object_id=object_id)
        if not self.is_dir(root_info):
            data = [self.map_file_data(root_info)]
        else:

            file_contents = self.get_paginated_results(
                files_client=files_client,
                object_id=object_id,
                extensions=extensions,
                recursive=recursive,
                previous_path=root_info["name"],
            )
            data = [self.map_file_data(f=f) for f in file_contents]
        for d in data:
            d.metadata.record_locator["drive_id"]: object_id
        return data

    def run(self, **kwargs: Any) -> Generator[FileData, None, None]:
        for f in self.get_files(
            files_client=self.connection_config.get_files_service(),
            object_id=self.connection_config.drive_id,
            recursive=self.index_config.recursive,
            extensions=self.index_config.extensions,
        ):
            yield f


@dataclass
class GoogleDriveDownloaderConfig(DownloaderConfig):
    pass


@dataclass
class GoogleDriveDownloader(Downloader):
    connection_config: GoogleDriveConnectionConfig
    download_config: GoogleDriveDownloaderConfig = field(
        default_factory=lambda: GoogleDriveDownloaderConfig()
    )
    connector_type: str = CONNECTOR_TYPE

    def get_download_path(self, file_data: FileData) -> Path:
        rel_path = file_data.source_identifiers.relative_path
        rel_path = rel_path[1:] if rel_path.startswith("/") else rel_path
        return self.download_dir / Path(rel_path)

    @SourceConnectionNetworkError.wrap
    def _get_content(self, downloader: "MediaIoBaseDownload") -> bool:
        downloaded = False
        while downloaded is False:
            _, downloaded = downloader.next_chunk()
        return downloaded

    def _write_file(self, file_data: FileData, file_contents: io.BytesIO):
        download_path = self.get_download_path(file_data=file_data)
        download_path.parent.mkdir(parents=True, exist_ok=True)
        logger.debug(f"writing {file_data.source_identifiers.fullpath} to {download_path}")
        with open(download_path, "wb") as handler:
            handler.write(file_contents.getbuffer())
        return self.generate_download_response(file_data=file_data, download_path=download_path)

    @requires_dependencies(["googleapiclient"], extras="google-drive")
    def run(self, file_data: FileData, **kwargs: Any) -> download_responses:
        from googleapiclient.http import MediaIoBaseDownload

        logger.debug(f"fetching file: {file_data.source_identifiers.fullpath}")
        mime_type = file_data.additional_metadata["mimeType"]
        record_id = file_data.identifier
        files_client = self.connection_config.get_files_service()
        if mime_type.startswith("application/vnd.google-apps"):
            export_mime = GOOGLE_DRIVE_EXPORT_TYPES.get(
                self.meta.get("mimeType"),  # type: ignore
            )
            if not export_mime:
                raise TypeError(
                    f"File not supported. Name: {file_data.source_identifiers.filename} "
                    f"ID: {record_id} "
                    f"MimeType: {mime_type}"
                )

            request = files_client.export_media(
                fileId=record_id,
                mimeType=export_mime,
            )
        else:
            request = files_client.get_media(fileId=record_id)

        file_contents = io.BytesIO()
        downloader = MediaIoBaseDownload(file_contents, request)
        downloaded = self._get_content(downloader=downloader)
        if not downloaded or not file_contents:
            return []
        return self._write_file(file_data=file_data, file_contents=file_contents)


google_drive_source_entry = SourceRegistryEntry(
    connection_config=GoogleDriveConnectionConfig,
    indexer_config=GoogleDriveIndexerConfig,
    indexer=GoogleDriveIndexer,
    downloader_config=GoogleDriveDownloaderConfig,
    downloader=GoogleDriveDownloader,
)
