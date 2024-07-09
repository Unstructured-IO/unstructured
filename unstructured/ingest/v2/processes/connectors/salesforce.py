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
from collections import OrderedDict
from dataclasses import dataclass, field
from email.utils import formatdate
from pathlib import Path
from string import Template
from textwrap import dedent
from typing import TYPE_CHECKING, Any, Generator, Type

from dateutil import parser

from unstructured.documents.elements import DataSourceMetadata
from unstructured.ingest.enhanced_dataclass import enhanced_field
from unstructured.ingest.error import SourceConnectionNetworkError
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
)
from unstructured.ingest.v2.logger import logger
from unstructured.ingest.v2.processes.connector_registry import (
    SourceRegistryEntry,
)
from unstructured.utils import requires_dependencies


class MissingCategoryError(Exception):
    """There are no categories with that name."""


CONNECTOR_TYPE = "salesforce"

if TYPE_CHECKING:
    from simple_salesforce import Salesforce

SALESFORCE_API_VERSION = "57.0"

# TODO: Add more categories as needed
ACCEPTED_CATEGORIES: list[str] = ["Account", "Case", "Campaign", "EmailMessage", "Lead"]

# Generic minimal email template used only
# to process EmailMessage records as .eml files
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
    def get_private_key_value_and_type(self) -> tuple[str, Type]:
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
    def get_client(self) -> "Salesforce":
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
    categories: list[str]


@dataclass
class SalesforceIndexer(Indexer):
    connection_config: SalesforceConnectionConfig
    index_config: SalesforceIndexerConfig

    def __post_init__(self):
        for record_type in self.index_config.categories:
            if record_type not in ACCEPTED_CATEGORIES:
                raise ValueError(f"{record_type} not currently an accepted Salesforce category")

    def get_file_extension(self, record_type) -> str:
        if record_type == "EmailMessage":
            extension = ".eml"
        elif record_type in ["Account", "Lead", "Case", "Campaign"]:
            extension = ".xml"
        else:
            raise MissingCategoryError(
                f"There are no categories with the name: {record_type}",
            )
        return extension

    @requires_dependencies(["simple_salesforce"], extras="salesforce")
    def list_files(self) -> list[FileData]:
        """Get Salesforce Ids for the records.
        Send them to next phase where each doc gets downloaded into the
        appropriate format for partitioning.
        """
        from simple_salesforce.exceptions import SalesforceMalformedRequest

        client = self.connection_config.get_client()

        files_list = []
        for record_type in self.index_config.categories:
            try:
                # Get ids from Salesforce
                records = client.query_all_iter(
                    f"select Id, SystemModstamp, CreatedDate, LastModifiedDate from {record_type}",
                )
                for record in records:
                    record_with_extension = record["Id"] + self.get_file_extension(
                        record["attributes"]["type"]
                    )
                    files_list.append(
                        FileData(
                            connector_type=CONNECTOR_TYPE,
                            identifier=record["Id"],
                            source_identifiers=SourceIdentifiers(
                                filename=record_with_extension,
                                fullpath=f"{record['attributes']['type']}/{record_with_extension}",
                            ),
                            metadata=DataSourceMetadata(
                                url=record["attributes"]["url"],
                                version=str(parser.parse(record["SystemModstamp"]).timestamp()),
                                date_created=str(parser.parse(record["CreatedDate"]).timestamp()),
                                date_modified=str(
                                    parser.parse(record["LastModifiedDate"]).timestamp()
                                ),
                                record_locator={"id": record["Id"]},
                            ),
                            additional_metadata={"record_type": record["attributes"]["type"]},
                        )
                    )
            except SalesforceMalformedRequest as e:
                raise SalesforceMalformedRequest(f"Problem with Salesforce query: {e}")

        return files_list

    def run(self, **kwargs: Any) -> Generator[FileData, None, None]:
        for f in self.list_files():
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

    def get_download_path(self, file_data: FileData) -> Path:
        rel_path = file_data.source_identifiers.relative_path
        rel_path = rel_path[1:] if rel_path.startswith("/") else rel_path
        return self.download_dir / Path(rel_path)

    def _xml_for_record(self, record: OrderedDict) -> str:
        """Creates partitionable xml file from a record"""
        import xml.etree.ElementTree as ET

        def create_xml_doc(data, parent, prefix=""):
            for key, value in data.items():
                if isinstance(value, OrderedDict):
                    create_xml_doc(value, parent, prefix=f"{prefix}{key}.")
                else:
                    item = ET.Element("item")
                    item.text = f"{prefix}{key}: {value}"
                    parent.append(item)

        root = ET.Element("root")
        create_xml_doc(record, root)

        xml_string = ET.tostring(root, encoding="utf-8", xml_declaration=True).decode()
        return xml_string

    def _eml_for_record(self, email_json: dict[str, Any]) -> str:
        """Recreates standard expected .eml format using template."""
        eml = EMAIL_TEMPLATE.substitute(
            date=formatdate(parser.parse(email_json.get("MessageDate")).timestamp()),
            message_identifier=email_json.get("MessageIdentifier"),
            subject=email_json.get("Subject"),
            from_email=email_json.get("FromAddress"),
            to_email=email_json.get("ToAddress"),
            textbody=email_json.get("TextBody"),
            htmlbody=email_json.get("HtmlBody"),
        )
        return dedent(eml)

    @SourceConnectionNetworkError.wrap
    def _get_response(self, file_data: FileData) -> OrderedDict:
        client = self.connection_config.get_client()
        return client.query(
            f"select FIELDS(STANDARD) from {file_data.additional_metadata['record_type']} where Id='{file_data.identifier}'",  # noqa: E501
        )

    def get_record(self, file_data: FileData) -> OrderedDict:
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
        record = self.get_record(file_data)

        try:
            if file_data.additional_metadata["record_type"] == "EmailMessage":
                document = self._eml_for_record(record)
            else:
                document = self._xml_for_record(record)
            download_path = self.get_download_path(file_data=file_data)
            download_path.parent.mkdir(parents=True, exist_ok=True)

            with open(download_path, "w") as page_file:
                page_file.write(document)

        except Exception as e:
            logger.error(f"failed to download file {file_data.identifier}: {e}", exc_info=True)
            raise SourceConnectionNetworkError(f"failed to download file {file_data.identifier}")

        return self.generate_download_response(file_data=file_data, download_path=download_path)


salesforce_source_entry = SourceRegistryEntry(
    connection_config=SalesforceConnectionConfig,
    indexer_config=SalesforceIndexerConfig,
    indexer=SalesforceIndexer,
    downloader_config=SalesforceDownloaderConfig,
    downloader=SalesforceDownloader,
)
