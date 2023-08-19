import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Type, List
import json
from textwrap import dedent

from email.utils import formatdate
from dateutil import parser

from string import Template


from unstructured.ingest.interfaces import (
    BaseConnector,
    BaseConnectorConfig,
    BaseIngestDoc,
    ConnectorCleanupMixin,
    IngestDocCleanupMixin,
    StandardConnectorConfig,
)
from unstructured.ingest.logger import logger
from unstructured.utils import requires_dependencies

from simple_salesforce import Salesforce

class MissingCategoryError(Exception):
    """There are no categories with that name."""

email_template = Template(
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
$textbody
--00000000000095c9b205eff92630--
""",
)

account_template = Template(
    """Id: $id
Name: $name
Type: $account_type
Phone: $phone
AccountNumber: $account_number
Website: $website
Industry: $industry
AnnualRevenue: $annual_revenue
NumberOfEmployees: $number_employees
Ownership: $ownership
TickerSymbol: $ticker_symbol
Description: $description
Rating: $rating
DandbCompanyId: $dnb_id
""",
)

lead_template = Template(
    """Id: $id
Name: $name
Title: $title
Company: $company
Phone: $phone
Email: $email
Website: $website
Description: $description
LeadSource: $lead_source
Rating: $rating
Status: $status
Industry: $industry
""",
)


@dataclass
class SimpleSalesforceConfig(BaseConnectorConfig):
    """Connector specific attributes"""

    salesforce_categories: List[str]
    salesforce_username: str
    salesforce_consumer_key: str
    salesforce_private_key_path: str
    recursive: bool = False

    @staticmethod
    def parse_folders(folder_str: str) -> List[str]:
        """Parses a comma separated string of Outlook folders into a list."""
        return [x.strip() for x in folder_str.split(",")]


@dataclass
class SalesforceIngestDoc(IngestDocCleanupMixin, BaseIngestDoc):
    record_type: str
    record: str
    config: SimpleSalesforceConfig
    file_exists: bool = False
    check_exists: bool = False

    def _tmp_download_file(self):
        if self.record_type == "EmailMessage":
            record_file = self.record["Id"] + ".eml"
        elif self.record_type in ["Account","Lead"]:
            record_file = self.record["Id"] + ".txt"
        else:
            raise MissingCategoryError(
                f"There are no categories with the name: {self.record_type}",
            )
        return Path(self.standard_config.download_dir) / self.record_type / record_file

    @property
    def _output_filename(self):
        record_file = self.record["Id"] + ".json"
        return Path(self.standard_config.output_dir) / self.record_type / record_file

    def _create_full_tmp_dir_path(self):
        self._tmp_download_file().parent.mkdir(parents=True, exist_ok=True)

    def create_account(self, account_json):
        """Creates partitionable account file"""
        account = account_template.substitute(
            id=account_json.get("Id"),
            name=account_json.get("Name"),
            account_type=account_json.get("Type"),
            phone=account_json.get("Phone"),
            account_number=account_json.get("AccountNumber"),
            website=account_json.get("Website"),
            industry=account_json.get("Industry"),
            annual_revenue=account_json.get("AnnualRevenue"),
            number_employees=account_json.get("NumberOfEmployees"),
            ownership=account_json.get("Ownership"),
            ticker_symbol=account_json.get("TickerSymbol"),
            description=account_json.get("Description"),
            rating=account_json.get("Rating"),
            dnb_id=account_json.get("DandbCompanyId"),
        )
        return dedent(account)

    def create_lead(self, lead_json):
        """Creates partitionable account file"""
        lead = lead_template.substitute(
            id=lead_json.get("Id"),
            name=lead_json.get("Name"),
            title=lead_json.get("Title"),
            company=lead_json.get("Company"),
            phone=lead_json.get("Phone"),
            email=lead_json.get("Email"),
            website=lead_json.get("Website"),
            description=lead_json.get("Description"),
            lead_source=lead_json.get("LeadSource"),
            rating=lead_json.get("Rating"),
            status=lead_json.get("Status"),
            industry=lead_json.get("Industry"),
        )
        return dedent(lead)

    def create_eml(self, email_json):
        """Recreates standard expected email format using template."""
        eml = email_template.substitute(
            date=formatdate(parser.parse(email_json.get("MessageDate")).timestamp()),
            message_identifier=email_json.get("MessageIdentifier"),
            subject=email_json.get("Subject"),
            from_email=email_json.get("FromAddress"),
            to_email=email_json.get("ToAddress"),
            textbody=email_json.get("TextBody"),
        )
        return dedent(eml)

    @BaseIngestDoc.skip_if_file_exists
    @requires_dependencies(["simple_salesforce"], extras="salesforce")
    def get_file(self):
        """Saves individual json records locally."""
        self._create_full_tmp_dir_path()

        # logger.debug(f"Writing page {self.record.get('Id')} - PID: {os.getpid()}")

        try:
            print("******** TRYING")
            # self.check_exists = True
            # self.file_exists = True
            if self.record_type == "EmailMessage":
                formatted_record = self.create_eml(self.record)
            elif self.record_type == "Account":
                formatted_record = self.create_account(self.record)
            elif self.record_type == "Lead":
                formatted_record = self.create_lead(self.record)
            else:
                raise MissingCategoryError(
                    f"There are no categories with the name: {self.record_type}",
                )

            with open(self._tmp_download_file(), "w") as page_file:
                page_file.write(formatted_record)

        except Exception as e:
            print("*******except ")
            print(e)
            # if error.code == APIErrorCode.ObjectNotFound:
            #     self.check_exists = True
            #     self.file_exists = False
            # else:
            #     self.config.get_logger().error(f"Error: {error}")

    @property
    def filename(self):
        """The filename of the file created from a BLABLABLA notion page"""
        return self._tmp_download_file()


@requires_dependencies(["simple_salesforce"], extras="salesforce")
class SalesforceConnector(ConnectorCleanupMixin, BaseConnector):
    ingest_doc_cls: Type[SalesforceIngestDoc] = SalesforceIngestDoc
    config: SimpleSalesforceConfig

    def __init__(
        self,
        config: SimpleSalesforceConfig,
        standard_config: StandardConnectorConfig,
    ) -> None:
        super().__init__(standard_config, config)

    def initialize(self):
        pass

    def get_ingest_docs(self):
        """Get json files from Salesforce.
        Create individual IngestDocs for each json entry in the appropriate category.
        Send them to next phase where each doc gets converted into the appropriate format for partitioning.
        """
        client = Salesforce(
            username=self.config.salesforce_username,
            consumer_key=self.config.salesforce_consumer_key,
            privatekey_file=self.config.salesforce_private_key_path,
        )

        doc_list = []
        #######TODO: Try Except empty
        for record_type in self.config.salesforce_categories:
            records = client.query_all(f"select FIELDS(STANDARD) from {record_type}")
            for record in records["records"]:
                doc_list.append(
                    SalesforceIngestDoc(
                        self.standard_config, self.config, record_type, record,
                    ),
                )
        print(doc_list)

        return doc_list
