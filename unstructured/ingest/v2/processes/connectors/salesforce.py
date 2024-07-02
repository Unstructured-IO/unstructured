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


@dataclass
class SalesforceIndexerConfig(IndexerConfig):
    categories: t.List[str]
    record_type: str = None
    record_id: str = None
    registry_name: str = "salesforce"
    _record: OrderedDict = field(default_factory=lambda: OrderedDict())
    recursive: bool = False



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
                        FileData(
                            connector_type=CONNECTOR_TYPE,
                            identifier=record["Id"],
                            source_identifiers=SourceIdentifiers(
                                filename=record["Id"],
                                # fullpath=record["attributes"]["url"], # fix this
                                # rel_path=record["attributes"]["url"],
                                fullpath=f"{record['attributes']['type']}/{record['Id']}",
                                ),
                            metadata=DataSourceMetadata(
                                url=record["attributes"]["url"],
                                version=record["SystemModstamp"],
                                date_created=record["CreatedDate"],
                                date_modified=record["LastModifiedDate"],
                                record_locator={"id": record["Id"]},
                            ),
                            additional_metadata={"record_type":record["attributes"]["type"]},


                        )
                    )
            except SalesforceMalformedRequest as e:
                raise SalesforceMalformedRequest(f"Problem with Salesforce query: {e}")

        return ingest_docs

        
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


@dataclass
class SalesforceDownloaderConfig(DownloaderConfig):
    pass


@dataclass
class SalesforceDownloader(Downloader):
    connection_config: SalesforceConnectionConfig
    download_config: SalesforceDownloaderConfig = field(
        default_factory=lambda: SalesforceDownloaderConfig()
    )
    connector_type: str = CONNECTOR_TYPE

    def is_async(self) -> bool:
        # return False
        return True

    def get_file_extension(self, record_type) -> str:
        print("********* get_file_extension ******")
        if record_type == "EmailMessage":
            extension = ".eml"
        elif record_type in ["Account", "Lead", "Case", "Campaign"]:
            extension = ".xml"
        else:
            raise MissingCategoryError(
                f"There are no categories with the name: {record_type}",
            )
        return extension


    def get_download_path(self, file_data: FileData) -> Path:
        print("********* _tmp_download_file ******")
        record_file =  file_data.identifier + self.get_file_extension(file_data.additional_metadata['record_type'])

        print(Path(self.download_dir) / file_data.additional_metadata['record_type'] / record_file)
        return Path(self.download_dir) / file_data.additional_metadata['record_type'] / record_file


    def _xml_for_record(self, record: OrderedDict) -> str:
        """Creates partitionable xml file from a record"""
        print("********* _xml_for_record ******")
        import xml.etree.ElementTree as ET

        def flatten_dict(data, parent, prefix=""):
            print("********* _flatten_dict ******")
            for key, value in data.items():
                if isinstance(value, OrderedDict):
                    flatten_dict(value, parent, prefix=f"{prefix}{key}.")
                else:
                    item = ET.Element("item")
                    item.text = f"{prefix}{key}: {value}"
                    parent.append(item)

        root = ET.Element("root")
        flatten_dict(record, root)
        xml_string = ET.tostring(root, encoding="utf-8", xml_declaration=True).decode()
        return xml_string

    def _eml_for_record(self, email_json: t.Dict[str, t.Any]) -> str:
        from dateutil import parser  # type: ignore
        print("********* _eml_for_record ******")

        """Recreates standard expected .eml format using template."""
        eml = EMAIL_TEMPLATE.substitute(
            date=formatdate(parser.parse(email_json.get("MessageDate")).timestamp()),
            message_identifier=email_json.get("MessageIdentifier"),
            subject=email_json.get("Subject"),
            from_email=email_json.get("FromAddress"),
            to_email=email_json.get("ToAddress"),
            textbody=email_json.get("TextBody"),
            # TODO: This is a hack to get emails to process correctly.
            # The HTML partitioner seems to have issues with <br> and text without tags like <p>
            htmlbody=email_json.get("HtmlBody", "")  # "" because you can't .replace None
            .replace("<br />", "<p>")
            .replace("<body", "<body><p"),
        )
        return dedent(eml)

    @SourceConnectionNetworkError.wrap
    def _get_response(self, file_data: FileData):
        print("********* _get_response ******")
        client = self.connection_config.get_client()
        return client.query_all(
            f"select FIELDS(STANDARD) from {file_data.additional_metadata['record_type']} where Id='{file_data.identifier}'",
        )

    def get_record(self, file_data: FileData) -> OrderedDict:
        print("********* get_record ******")
        # Get record from Salesforce based on id
        response = self._get_response(file_data)
        logger.debug(f"response was returned for salesforce record id: {file_data.identifier}")
        records = response["records"]
        if not records:
            raise ValueError(
                f"No record found with record id {file_data.identifier}: {json.dumps(response)}"
            )
        record_json = records[0]
        return record_json

    def run(self, file_data: FileData, **kwargs: Any) -> DownloadResponse:
        # breakpoint()
        record=self.get_record(file_data)
        # breakpoint()

        record_id = file_data.identifier

        try:
            if file_data.additional_metadata['record_type'] == "EmailMessage":
                document = self._eml_for_record(record)
            else:
                document = self._xml_for_record(record)
            download_path = self.get_download_path(file_data=file_data)
            download_path.parent.mkdir(parents=True, exist_ok=True)
            # breakpoint()
            with open(download_path, "w") as page_file:
                page_file.write(document)
            return DownloadResponse(
                file_data=file_data, path=Path(download_path),
            )

        except Exception as e:
            logger.error(
                f"Error while downloading and saving file: {file_data.identifier}.",
            )
            logger.error(e)




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
