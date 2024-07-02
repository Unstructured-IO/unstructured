"""
Salesforce Connector
Able to download Account, Case, Campaign, EmailMessage, Lead
Salesforce returns everything as a list of json.
This saves each entry as a separate file to be partitioned.
Using JWT authorization
https://developer.salesforce.com/docs/atlas.en-us.sfdx_dev.meta/sfdx_dev/sfdx_dev_auth_key_and_cert.htm
https://developer.salesforce.com/docs/atlas.en-us.sfdx_dev.meta/sfdx_dev/sfdx_dev_auth_connected_app.htm
"""
import json
import typing as t
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import datetime
from email.utils import formatdate
from pathlib import Path
from string import Template
from textwrap import dedent
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
    DownloadResponse,
    FileData,
    Indexer,
    IndexerConfig,
    SourceIdentifiers,
    download_responses,
)
from unstructured.ingest.v2.logger import logger
from unstructured.ingest.v2.processes.connector_registry import (
    SourceRegistryEntry,
    add_source_entry,
)
from unstructured.utils import requires_dependencies

CONNECTOR_TYPE = "salesforce"

if TYPE_CHECKING:
    from googleapiclient.discovery import Resource as GoogleAPIResource
    from googleapiclient.http import MediaIoBaseDownload

SALESFORCE_API_VERSION = "57.0"

ACCEPTED_CATEGORIES = ["Account", "Case", "Campaign", "EmailMessage", "Lead"]

EMAIL_TEMPLATE = Template(
    """MIME-Version: 1.0
Date: $date
Message-ID: $message_identifier
Subject: $subject
From: $from_email
To: $to_email
Content-Type: multipart/alternative; boundary="00000000000095c9b205eff92630"
--00000000000095c9b205eff92630
Content-Type: text/plain; charset="UTF-8"
$textbody
--00000000000095c9b205eff92630
Content-Type: text/html; charset="UTF-8"
$htmlbody
--00000000000095c9b205eff92630--
""",
)



@dataclass
class SalesforceAccessConfig(AccessConfig):
    consumer_key: str
    private_key: str

    @requires_dependencies(["cryptography"])
    def get_private_key_value_and_type(self) -> t.Tuple[str, t.Type]:
        from cryptography.hazmat.primitives import serialization

        try:
            serialization.load_pem_private_key(data=self.private_key.encode("utf-8"), password=None)
        except ValueError:
            pass
        else:
            return self.private_key, str

        if Path(self.private_key).is_file():
            return self.private_key, Path

        raise ValueError("private_key does not contain PEM private key or path")



@dataclass
class SalesforceConnectionConfig(ConnectionConfig):
    username: str
    access_config: SalesforceAccessConfig = enhanced_field(sensitive=True)

    @requires_dependencies(["simple_salesforce"], extras="salesforce")
    def get_client(self):
        from simple_salesforce import Salesforce

        pkey_value, pkey_type = self.access_config.get_private_key_value_and_type()

        return Salesforce(
            username=self.username,
            consumer_key=self.access_config.consumer_key,
            privatekey_file=pkey_value if pkey_type is Path else None,
            privatekey=pkey_value if pkey_type is str else None,
            version=SALESFORCE_API_VERSION,
        )
    # drive_id: str
    # access_config: GoogleDriveAccessConfig = enhanced_field(sensitive=True)

    # @requires_dependencies(["googleapiclient"], extras="google-drive")
    # def get_files_service(self) -> "GoogleAPIResource":
    #     from google.auth import default, exceptions
    #     from google.oauth2 import service_account
    #     from googleapiclient.discovery import build
    #     from googleapiclient.errors import HttpError

    #     # Service account key can be a dict or a file path(str)
    #     # But the dict may come in as a string
    #     if isinstance(self.access_config.service_account_key, str):
    #         key_path = json_to_dict(self.access_config.service_account_key)
    #     elif isinstance(self.access_config.service_account_key, dict):
    #         key_path = self.access_config.service_account_key
    #     else:
    #         raise TypeError(
    #             f"access_config.service_account_key must be "
    #             f"str or dict, got: {type(self.access_config.service_account_key)}"
    #         )

    #     try:
    #         if isinstance(key_path, dict):
    #             creds = service_account.Credentials.from_service_account_info(key_path)
    #         elif isinstance(key_path, str):
    #             os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = key_path
    #             creds, _ = default()
    #         else:
    #             raise ValueError(
    #                 f"key path not recognized as a dictionary or a file path: "
    #                 f"[{type(key_path)}] {key_path}",
    #             )
    #         service = build("drive", "v3", credentials=creds)
    #         return service.files()

    #     except HttpError as exc:
    #         raise ValueError(f"{exc.reason}")
    #     except exceptions.DefaultCredentialsError:
    #         raise ValueError("The provided API key is invalid.")


@dataclass
class SalesforceIndexerConfig(IndexerConfig):
    categories: t.List[str]
    record_type: str = None
    record_id: str = None
    registry_name: str = "salesforce"
    _record: OrderedDict = field(default_factory=lambda: OrderedDict())
    recursive: bool = False









    # extensions: Optional[list[str]] = None
    # recursive: bool = False

    # def __post_init__(self):
    #     # Strip leading period of extension
    #     if self.extensions is not None:
    #         self.extensions = [e[1:] if e.startswith(".") else e for e in self.extensions]


@dataclass
class SalesforceIndexer(Indexer):
    connection_config: SalesforceConnectionConfig
    index_config: SalesforceIndexerConfig


    @requires_dependencies(["simple_salesforce"], extras="salesforce")
    def get_ingest_docs(self) -> t.List[FileData]:
        print("********* get_ingest_docs ******")
        """Get Salesforce Ids for the records.
        Send them to next phase where each doc gets downloaded into the
        appropriate format for partitioning.
        """
        from simple_salesforce.exceptions import SalesforceMalformedRequest

        client = self.connection_config.get_client()
        # breakpoint()

        ingest_docs = []
        for record_type in self.index_config.categories:
            if record_type not in ACCEPTED_CATEGORIES:
                raise ValueError(f"{record_type} not currently an accepted Salesforce category")

            try:
                # Get ids from Salesforce
                records = client.query_all(
                    # "select {Id} from EmailMessage",
                    f"select Id, SystemModstamp, CreatedDate, LastModifiedDate from {record_type}",

                    # also try query_all_iter
                )
                for record in records["records"]:
                    # breakpoint()
                    ingest_docs.append(
                        # SalesforceIngestDoc(
                        #     connector_config=self.connector_config,
                        #     processor_config=self.processor_config,
                        #     read_config=self.read_config,
                        #     record_type=record_type,
                        #     record_id=record["Id"],
                        # ),
                        # record["Id"]
#             data = sf.query_all_iter("SELECT Id, Email FROM Contact WHERE LastName = 'Jones'")
# for row in data:
#   process(row)

            #             OrderedDict([('attributes',
            #   OrderedDict([('type', 'EmailMessage'),
            #                ('url',
            #                 '/services/data/v57.0/sobjects/EmailMessage/02sHu00001efErPIAU')])),
            #  ('Id', '02sHu00001efErPIAU')])
                        FileData(
                            connector_type=CONNECTOR_TYPE,
                            identifier=record["Id"],
                            source_identifiers=SourceIdentifiers(
                                filename=record["Id"],
                                fullpath=record["attributes"]["url"],
                                rel_path=record["attributes"]["url"],
                                ),
                            metadata=DataSourceMetadata(
                                url=record["attributes"]["url"],
                                version=record["SystemModstamp"],
                                date_created=record["CreatedDate"],
                                date_modified=record["LastModifiedDate"],
                                record_locator={"id": record["Id"]},
                            ),
                            additional_metadata={"type":record["attributes"]["type"]},


                        )
                    )
            except SalesforceMalformedRequest as e:
                raise SalesforceMalformedRequest(f"Problem with Salesforce query: {e}")

        return ingest_docs

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
        # breakpoint()
        for f in self.get_ingest_docs():
            # files_client=self.connection_config.get_files_service(),
            # object_id=self.connection_config.drive_id,
            # recursive=self.index_config.recursive,
            # extensions=self.index_config.extensions,
        # ):

            
            print(f"********* run ****** {f}")
            yield f



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
        url = f.pop("webContentLink")
        version = f.pop("version", None)
        permissions = f.pop("permissions", None)
        date_created_str = f.pop("createdTime")
        date_created_dt = parser.parse(date_created_str)
        date_modified_str = f.pop("modifiedTime")
        parent_path = f.pop("parent_path", None)
        parent_root_path = f.pop("parent_root_path", None)
        date_modified_dt = parser.parse(date_modified_str)
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

    # def run(self, **kwargs: Any) -> Generator[FileData, None, None]:
    #     for f in self.get_files(
    #         files_client=self.connection_config.get_files_service(),
    #         object_id=self.connection_config.drive_id,
    #         recursive=self.index_config.recursive,
    #         extensions=self.index_config.extensions,
    #     ):
    #         yield f


@dataclass
class SalesforceDownloaderConfig(DownloaderConfig):
    pass


@dataclass
class SalesforceDownloader(Downloader):
    connection_config: SalesforceConnectionConfig
    download_config: SalesforceDownloaderConfig = field(
        default_factory=lambda: SalesforceDownloaderConfig()
    )
    def run(self, file_data: FileData, **kwargs: Any) -> download_responses:
        pass













    # connection_config: GoogleDriveConnectionConfig
    # download_config: GoogleDriveDownloaderConfig = field(
    #     default_factory=lambda: GoogleDriveDownloaderConfig()
    # )
    # connector_type: str = CONNECTOR_TYPE

    # def get_download_path(self, file_data: FileData) -> Path:
    #     rel_path = file_data.source_identifiers.relative_path
    #     rel_path = rel_path[1:] if rel_path.startswith("/") else rel_path
    #     return self.download_dir / Path(rel_path)

    # @SourceConnectionNetworkError.wrap
    # def _get_content(self, downloader: "MediaIoBaseDownload") -> bool:
    #     downloaded = False
    #     while downloaded is False:
    #         _, downloaded = downloader.next_chunk()
    #     return downloaded

    # @staticmethod
    # def is_float(value: str):
    #     try:
    #         float(value)
    #         return True
    #     except ValueError:
    #         return False

    # def _write_file(self, file_data: FileData, file_contents: io.BytesIO):
    #     download_path = self.get_download_path(file_data=file_data)
    #     download_path.parent.mkdir(parents=True, exist_ok=True)
    #     logger.debug(f"writing {file_data.source_identifiers.fullpath} to {download_path}")
    #     with open(download_path, "wb") as handler:
    #         handler.write(file_contents.getbuffer())
    #     if (
    #         file_data.metadata.date_modified
    #         and self.is_float(file_data.metadata.date_modified)
    #         and file_data.metadata.date_created
    #         and self.is_float(file_data.metadata.date_created)
    #     ):
    #         date_modified = float(file_data.metadata.date_modified)
    #         date_created = float(file_data.metadata.date_created)
    #         os.utime(download_path, times=(date_created, date_modified))
    #     return DownloadResponse(file_data=file_data, path=download_path)

    # @requires_dependencies(["googleapiclient"], extras="google-drive")
    # def run(self, file_data: FileData, **kwargs: Any) -> download_responses:
    #     from googleapiclient.http import MediaIoBaseDownload

    #     logger.debug(f"fetching file: {file_data.source_identifiers.fullpath}")
    #     mime_type = file_data.additional_metadata["mimeType"]
    #     record_id = file_data.identifier
    #     files_client = self.connection_config.get_files_service()
    #     if mime_type.startswith("application/vnd.google-apps"):
    #         export_mime = GOOGLE_DRIVE_EXPORT_TYPES.get(
    #             self.meta.get("mimeType"),  # type: ignore
    #         )
    #         if not export_mime:
    #             raise TypeError(
    #                 f"File not supported. Name: {file_data.source_identifiers.filename} "
    #                 f"ID: {record_id} "
    #                 f"MimeType: {mime_type}"
    #             )

    #         request = files_client.export_media(
    #             fileId=record_id,
    #             mimeType=export_mime,
    #         )
    #     else:
    #         request = files_client.get_media(fileId=record_id)

    #     file_contents = io.BytesIO()
    #     downloader = MediaIoBaseDownload(file_contents, request)
    #     downloaded = self._get_content(downloader=downloader)
    #     if not downloaded or not file_contents:
    #         return []
    #     return self._write_file(file_data=file_data, file_contents=file_contents)


add_source_entry(
    source_type=CONNECTOR_TYPE,
    entry=SourceRegistryEntry(
        connection_config=SalesforceConnectionConfig,
        indexer_config=SalesforceIndexerConfig,
        indexer=SalesforceIndexer,
        downloader_config=SalesforceDownloaderConfig,
        downloader=SalesforceDownloader,
    ),
)
