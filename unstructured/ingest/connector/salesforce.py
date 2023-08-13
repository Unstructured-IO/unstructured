import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Type, List
import json
from textwrap import dedent


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

    sql: str
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
        page_file = "hello" + ".eml"
        return Path(self.standard_config.download_dir) / page_file

    @property
    def _output_filename(self):
        # page_file = self.page_id + ".json"
        page_file = "hello" + ".json"
        return Path(self.standard_config.output_dir) / page_file

    def _create_full_tmp_dir_path(self):
        self._tmp_download_file().parent.mkdir(parents=True, exist_ok=True)

    def create_eml(self, email_json):
        print("*&**")
        print("Date: Fri, 16 Dec 2022 17:04:16 -0500")
        print(email_json["MessageDate"])
        html_body_1_line = email_json["HtmlBody"].replace("\n","").replace("\r","").replace("\t","")
        eml = f"""MIME-Version: 1.0
Date: Fri, 16 Dec 2022 17:04:16 -0500
Message-ID: {email_json["MessageIdentifier"]}
Subject: {email_json["Subject"]}
From: {email_json["FromAddress"]}
To: {email_json["ToAddress"]}
Content-Type: multipart/alternative; boundary="00000000000095c9b205eff92630"

--00000000000095c9b205eff92630
Content-Type: text/plain; charset="UTF-8"

{email_json["TextBody"]}

--00000000000095c9b205eff92630
Content-Type: text/html; charset="UTF-8"
{email_json["TextBody"]}
--00000000000095c9b205eff92630--
"""

        return dedent(eml)

    @BaseIngestDoc.skip_if_file_exists
    @requires_dependencies(["simple_salesforce"], extras="salesforce")
    def get_file(self):
        print("GET FILE!!!!!!")
        self._create_full_tmp_dir_path()

        # self.config.get_logger().debug(f"fetching page {self.page_id} - PID: {os.getpid()}")
        logger.debug(f"fetching page BOB - PID: {os.getpid()}")

        # client = NotionClient(auth=self.api_key, logger=self.config.get_logger())

        client = Salesforce(username=self.config.salesforce_username, 
                            password=self.config.salesforce_password, 
                            security_token=self.config.salesforce_token)

        try:
            # text_extraction = extract_page_text(
            #     client=client,
            #     page_id=self.page_id,
            #     logger=self.config.get_logger(),
            # )
            # self.check_exists = True
            # self.file_exists = True
            # if text_extraction.text:
            rsp = client.query_all(self.sql)
            # breakpoint()
            for record in rsp["records"]:
                eml = self.create_eml(record)

                # breakpoint()
                with open(self._tmp_download_file(), "w") as page_file:
                    page_file.write(eml)

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
        """The filename of the file created from a notion page"""
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
        # Create appropriate sql
        sql_list=[]
        for categrory in self.config.salesforce_categories:
            print(categrory)
            sql_list.append("select FIELDS(STANDARD) from EmailMessage")
        print("***********")
        print(sql_list)
        return [SalesforceIngestDoc(self.standard_config, self.config, f) for f in sql_list]


