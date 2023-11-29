"""
Salesforce Connector
Able to download Account, Case, Campaign, EmailMessage, Lead
Salesforce returns everything as a list of json.
This saves each entry as a separate file to be partitioned.
Using JWT authorization
https://developer.salesforce.com/docs/atlas.en-us.sfdx_dev.meta/sfdx_dev/sfdx_dev_auth_key_and_cert.htm
https://developer.salesforce.com/docs/atlas.en-us.sfdx_dev.meta/sfdx_dev/sfdx_dev_auth_connected_app.htm
"""
import os
import typing as t
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import datetime
from email.utils import formatdate
from pathlib import Path
from string import Template
from textwrap import dedent

from dateutil import parser  # type: ignore

from unstructured.ingest.error import SourceConnectionError, SourceConnectionNetworkError
from unstructured.ingest.interfaces import (
    BaseConnectorConfig,
    BaseSingleIngestDoc,
    BaseSourceConnector,
    IngestDocCleanupMixin,
    SourceConnectorCleanupMixin,
    SourceMetadata,
)
from unstructured.ingest.logger import logger
from unstructured.utils import requires_dependencies


class MissingCategoryError(Exception):
    """There are no categories with that name."""


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
class SimpleSalesforceConfig(BaseConnectorConfig):
    """Connector specific attributes"""

    categories: t.List[str]
    username: str
    consumer_key: str
    private_key_path: str
    recursive: bool = False

    @requires_dependencies(["simple_salesforce"], extras="salesforce")
    def get_client(self):
        from simple_salesforce import Salesforce

        return Salesforce(
            username=self.username,
            consumer_key=self.consumer_key,
            privatekey_file=self.private_key_path,
            version=SALESFORCE_API_VERSION,
        )


@dataclass
class SalesforceIngestDoc(IngestDocCleanupMixin, BaseSingleIngestDoc):
    connector_config: SimpleSalesforceConfig
    record_type: str
    record_id: str
    registry_name: str = "salesforce"
    _record: OrderedDict = field(default_factory=lambda: OrderedDict())

    @property
    def record(self):
        if not self._record:
            self._record = self.get_record()
        return self._record

    def _tmp_download_file(self) -> Path:
        if self.record_type == "EmailMessage":
            record_file = self.record_id + ".eml"
        elif self.record_type in ["Account", "Lead", "Case", "Campaign"]:
            record_file = self.record_id + ".xml"
        else:
            raise MissingCategoryError(
                f"There are no categories with the name: {self.record_type}",
            )
        return Path(self.read_config.download_dir) / self.record_type / record_file

    @property
    def _output_filename(self) -> Path:
        record_file = self.record_id + ".json"
        return Path(self.processor_config.output_dir) / self.record_type / record_file

    def _create_full_tmp_dir_path(self):
        self._tmp_download_file().parent.mkdir(parents=True, exist_ok=True)

    def _xml_for_record(self, record: OrderedDict) -> str:
        """Creates partitionable xml file from a record"""
        import xml.etree.ElementTree as ET

        def flatten_dict(data, parent, prefix=""):
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
    def _get_response(self):
        client = self.connector_config.get_client()
        return client.query_all(
            f"select FIELDS(STANDARD) from {self.record_type} where Id='{self.record_id}'",
        )

    def get_record(self) -> OrderedDict:
        # Get record from Salesforce based on id
        response = self._get_response()
        logger.debug(f"response from salesforce record request: {response}")
        records = response["records"]
        if not records:
            raise ValueError(f"No record found with record id {self.record_id}: {response}")
        record_json = records[0]
        return record_json

    def update_source_metadata(self) -> None:  # type: ignore
        record_json = self.record

        date_format = "%Y-%m-%dT%H:%M:%S.000+0000"
        self.source_metadata = SourceMetadata(
            date_created=datetime.strptime(record_json["CreatedDate"], date_format).isoformat(),
            date_modified=datetime.strptime(
                record_json["LastModifiedDate"],
                date_format,
            ).isoformat(),
            # SystemModstamp is Timestamp if record has been modified by person or automated system
            version=record_json.get("SystemModstamp"),
            source_url=record_json["attributes"].get("url"),
            exists=True,
        )

    @SourceConnectionError.wrap
    @BaseSingleIngestDoc.skip_if_file_exists
    def get_file(self):
        """Saves individual json records locally."""
        self._create_full_tmp_dir_path()
        logger.debug(f"Writing file {self.record_id} - PID: {os.getpid()}")

        record = self.record

        self.update_source_metadata()

        try:
            if self.record_type == "EmailMessage":
                document = self._eml_for_record(record)
            else:
                document = self._xml_for_record(record)

            with open(self._tmp_download_file(), "w") as page_file:
                page_file.write(document)

        except Exception as e:
            logger.error(
                f"Error while downloading and saving file: {self.record_id}.",
            )
            logger.error(e)

    @property
    def filename(self):
        """The filename of the file created from a Salesforce record"""
        return self._tmp_download_file()


@dataclass
class SalesforceSourceConnector(SourceConnectorCleanupMixin, BaseSourceConnector):
    connector_config: SimpleSalesforceConfig

    def __post_init__(self):
        self.ingest_doc_cls: t.Type[SalesforceIngestDoc] = SalesforceIngestDoc

    def initialize(self):
        pass

    @requires_dependencies(["simple_salesforce"], extras="salesforce")
    def check_connection(self):
        from simple_salesforce.exceptions import SalesforceError

        try:
            self.connector_config.get_client()
        except SalesforceError as salesforce_error:
            logger.error(f"failed to validate connection: {salesforce_error}", exc_info=True)
            raise SourceConnectionError(f"failed to validate connection: {salesforce_error}")

    @requires_dependencies(["simple_salesforce"], extras="salesforce")
    def get_ingest_docs(self) -> t.List[SalesforceIngestDoc]:
        """Get Salesforce Ids for the records.
        Send them to next phase where each doc gets downloaded into the
        appropriate format for partitioning.
        """
        from simple_salesforce.exceptions import SalesforceMalformedRequest

        client = self.connector_config.get_client()

        ingest_docs = []
        for record_type in self.connector_config.categories:
            if record_type not in ACCEPTED_CATEGORIES:
                raise ValueError(f"{record_type} not currently an accepted Salesforce category")

            try:
                # Get ids from Salesforce
                records = client.query_all(
                    f"select Id from {record_type}",
                )
                for record in records["records"]:
                    ingest_docs.append(
                        SalesforceIngestDoc(
                            connector_config=self.connector_config,
                            processor_config=self.processor_config,
                            read_config=self.read_config,
                            record_type=record_type,
                            record_id=record["Id"],
                        ),
                    )
            except SalesforceMalformedRequest as e:
                raise SalesforceMalformedRequest(f"Problem with Salesforce query: {e}")

        return ingest_docs
