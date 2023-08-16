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



email_template = Template("""MIME-Version: 1.0
Date: $date
Message-ID: $id
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
"""
)

# TODO: Probably need new authentication

@dataclass
class SimpleSalesforceConfig(BaseConnectorConfig):
    """ Connector specific attributes"""
    salesforce_categories: List[str]
    salesforce_username: str
    salesforce_password: str
    salesforce_token: str
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
    # salesforce_username: str
    # salesforce_password: str
    # salesforce_token: str
    file_exists: bool = False
    check_exists: bool = False

    random_number = 5 

    def _tmp_download_file(self):
        # page_file = self.page_id + ".txt"
        # page_file = "hello" + ".txt"
        if self.record_type == "EmailMessage":
            record_file = self.record["Id"] + ".eml"
        elif self.record_type == "Account":
            record_file = self.record["Id"] + ".txt"
        return Path(self.standard_config.download_dir) / self.record_type / record_file

    @property
    def _output_filename(self):
        # page_file = self.page_id + ".json"
        record_file = self.record["Id"] + ".json"
        return Path(self.standard_config.output_dir) / self.record_type / record_file

    def _create_full_tmp_dir_path(self):
        self._tmp_download_file().parent.mkdir(parents=True, exist_ok=True)

    def create_txt(self, txt_json):
        txt = f"""
Name: {txt_json["Name"]}
        """
        return dedent(txt)

    def create_eml(self, email_json):
        ####### Fix Date format, should we use htmlbody or textbody
        print("*&**")
        print("Date: Fri, 16 Dec 2022 17:04:16 -0500")
        print(email_json["MessageDate"])
        html_body_1_line = email_json["HtmlBody"].replace("\n","").replace("\r","").replace("\t","")
        eml = email_template.substitute(date=formatdate(parser.parse(email_json["MessageDate"]).timestamp()),id=email_json["MessageIdentifier"],subject=email_json["Subject"],
                                      from_email=email_json["FromAddress"],to_email=email_json["ToAddress"],textbody=email_json["TextBody"])
        return dedent(eml)

    @BaseIngestDoc.skip_if_file_exists
    @requires_dependencies(["simple_salesforce"], extras="salesforce")
    def get_file(self):
        print("GET FILE!!!!!!")
        self._create_full_tmp_dir_path()

        # self.config.get_logger().debug(f"fetching page {self.page_id} - PID: {os.getpid()}")
        logger.debug(f"fetching page &&&&&&BOB - PID: {os.getpid()}")

        # client = NotionClient(auth=self.api_key, logger=self.config.get_logger())

        # client = Salesforce(username=self.config.salesforce_username, 
        #                     password=self.config.salesforce_password, 
        #                     security_token=self.config.salesforce_token)

        try:
            print("******** TRYING")
            # text_extraction = extract_page_text(
            #     client=client,
            #     page_id=self.page_id,
            #     logger=self.config.get_logger(),
            # )
            # self.check_exists = True
            # self.file_exists = True
            # if text_extraction.text:
            # rsp = client.query_all(self.sql)
            # breakpoint()
            # for record in rsp["records"]:
            if self.record_type == "EmailMessage":
                formatted_record = self.create_eml(self.record)
            elif self.record_type == "Account":
                formatted_record = self.create_txt(self.record)

            # breakpoint()
            with open(self._tmp_download_file(), "w") as page_file:
                page_file.write(formatted_record)

        # try:
        #     text_extraction = extract_page_text(
        #         client=client,
        #         page_id=self.page_id,
        #         logger=self.config.get_logger(),
        #     )
        #     self.check_exists = True
        #     self.file_exists = True
        #     if text_extraction.text:
        #         with open(self._tmp_download_file(), "w") as page_file:
        #             page_file.write(text_extraction.text)

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
        client = Salesforce(username=self.config.salesforce_username, 
                    password=self.config.salesforce_password, 
                    security_token=self.config.salesforce_token)
        # Create appropriate sql

        doc_list=[]
        for record_type in self.config.salesforce_categories:
            # print(record_type)
            records = client.query_all(f"select FIELDS(STANDARD) from {record_type}")
            for record in records["records"]:
                # print(record)
                doc_list.append(SalesforceIngestDoc(self.standard_config, self.config, record_type, record))

        return doc_list


