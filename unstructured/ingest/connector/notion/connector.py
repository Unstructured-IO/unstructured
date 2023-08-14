import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional
from uuid import UUID

from unstructured.ingest.connector.notion.types.database import Database
from unstructured.ingest.connector.notion.types.page import Page
from unstructured.ingest.interfaces import (
    BaseConnector,
    BaseConnectorConfig,
    BaseIngestDoc,
    ConnectorCleanupMixin,
    IngestDocCleanupMixin,
    StandardConnectorConfig,
)
from unstructured.ingest.logger import make_default_logger
from unstructured.utils import (
    requires_dependencies,
)


@dataclass
class SimpleNotionConfig(BaseConnectorConfig):
    """Connector config to process all messages by channel id's."""

    page_ids: List[str]
    database_ids: List[str]
    recursive: bool
    api_key: str
    verbose: bool
    logger: Optional[logging.Logger] = None

    @staticmethod
    def parse_ids(ids_str: str) -> List[str]:
        """Parses a comma separated list of ids into a list of UUID strings."""
        return [str(UUID(x.strip())) for x in ids_str.split(",")]

    def get_logger(self) -> logging.Logger:
        if self.logger:
            return self.logger
        return make_default_logger(logging.DEBUG if self.verbose else logging.INFO)


@dataclass
class NotionPageIngestDoc(IngestDocCleanupMixin, BaseIngestDoc):
    """Class encapsulating fetching a doc and writing processed results (but not
    doing the processing!).

    Also includes a cleanup method. When things go wrong and the cleanup
    method is not called, the file is left behind on the filesystem to assist debugging.
    """

    page_id: str
    api_key: str
    config: SimpleNotionConfig
    file_metadata: Optional[Page] = None
    file_exists: bool = False
    check_exists: bool = False

    def _tmp_download_file(self):
        page_file = self.page_id + ".html"
        return Path(self.standard_config.download_dir) / page_file

    @property
    def _output_filename(self):
        page_file = self.page_id + ".json"
        return Path(self.standard_config.output_dir) / page_file

    def _create_full_tmp_dir_path(self):
        self._tmp_download_file().parent.mkdir(parents=True, exist_ok=True)

    @BaseIngestDoc.skip_if_file_exists
    @requires_dependencies(dependencies=["notion_client"])
    def get_file(self):
        from notion_client import APIErrorCode, APIResponseError

        from unstructured.ingest.connector.notion.client import Client as NotionClient
        from unstructured.ingest.connector.notion.helpers import extract_page_html

        self._create_full_tmp_dir_path()

        self.config.get_logger().debug(f"fetching page {self.page_id} - PID: {os.getpid()}")

        client = NotionClient(auth=self.api_key, logger=self.config.get_logger())

        try:
            text_extraction = extract_page_html(
                client=client,
                page_id=self.page_id,
                logger=self.config.get_logger(),
            )
            self.check_exists = True
            self.file_exists = True
            if html := text_extraction.html:
                with open(self._tmp_download_file(), "w") as page_file:
                    page_file.write(html.render(pretty=True))

        except APIResponseError as error:
            if error.code == APIErrorCode.ObjectNotFound:
                self.check_exists = True
                self.file_exists = False
            else:
                self.config.get_logger().error(f"Error: {error}")

    @requires_dependencies(dependencies=["notion_client"])
    def get_file_metadata(self):
        from notion_client import APIErrorCode, APIResponseError

        from unstructured.ingest.connector.notion.client import Client as NotionClient

        client = NotionClient(auth=self.api_key, logger=self.config.get_logger())

        # The Notion block endpoint gives more hierarchical information (parent,child relationships)
        # than the pages endpoint so choosing to use that one to get metadata about the page
        try:
            self.file_metadata = client.pages.retrieve(page_id=self.page_id)  # type: ignore
            self.check_exists = True
            self.file_exists = True
        except APIResponseError as error:
            if error.code == APIErrorCode.ObjectNotFound:
                self.check_exists = True
                self.file_exists = False
            else:
                self.config.get_logger().error(f"Error: {error}")

    @property
    def date_created(self) -> Optional[str]:
        """The date the document was created on the source system."""
        if not self.file_metadata:
            self.get_file_metadata()

        return self.file_metadata.created_time if self.file_metadata else None

    @property
    def date_modified(self) -> Optional[str]:
        """The date the document was last modified on the source system."""
        if not self.file_metadata:
            self.get_file_metadata()

        return self.file_metadata.last_edited_time if self.file_metadata else None

    @property
    def exists(self) -> Optional[bool]:
        """Whether the document exists on the remote source."""
        if self.check_exists:
            return self.file_exists

        self.get_file_metadata()

        return self.file_exists

    @property
    def filename(self):
        """The filename of the file created from a notion page"""
        return self._tmp_download_file()


@dataclass
class NotionDatabaseIngestDoc(IngestDocCleanupMixin, BaseIngestDoc):
    """Class encapsulating fetching a doc and writing processed results (but not
    doing the processing!).

    Also includes a cleanup method. When things go wrong and the cleanup
    method is not called, the file is left behind on the filesystem to assist debugging.
    """

    database_id: str
    api_key: str
    config: SimpleNotionConfig
    file_metadata: Optional[Database] = None
    file_exists: bool = False
    check_exists: bool = False

    def _tmp_download_file(self):
        page_file = self.database_id + ".html"
        return Path(self.standard_config.download_dir) / page_file

    @property
    def _output_filename(self):
        page_file = self.database_id + ".json"
        return Path(self.standard_config.output_dir) / page_file

    def _create_full_tmp_dir_path(self):
        self._tmp_download_file().parent.mkdir(parents=True, exist_ok=True)

    @BaseIngestDoc.skip_if_file_exists
    @requires_dependencies(dependencies=["notion_client"])
    def get_file(self):
        from notion_client import APIErrorCode, APIResponseError

        from unstructured.ingest.connector.notion.client import Client as NotionClient
        from unstructured.ingest.connector.notion.helpers import extract_database_html

        self._create_full_tmp_dir_path()

        self.config.get_logger().debug(f"fetching database {self.database_id} - PID: {os.getpid()}")

        client = NotionClient(auth=self.api_key, logger=self.config.get_logger())

        try:
            text_extraction = extract_database_html(
                client=client,
                database_id=self.database_id,
                logger=self.config.get_logger(),
            )
            self.check_exists = True
            self.file_exists = True
            if html := text_extraction.html:
                with open(self._tmp_download_file(), "w") as page_file:
                    page_file.write(html.render(pretty=True))

        except APIResponseError as error:
            if error.code == APIErrorCode.ObjectNotFound:
                self.check_exists = True
                self.file_exists = False
            else:
                self.config.get_logger().error(f"Error: {error}")

    @requires_dependencies(dependencies=["notion_client"])
    def get_file_metadata(self):
        from notion_client import APIErrorCode, APIResponseError

        from unstructured.ingest.connector.notion.client import Client as NotionClient

        client = NotionClient(auth=self.api_key, logger=self.config.get_logger())

        # The Notion block endpoint gives more hierarchical information (parent,child relationships)
        # than the pages endpoint so choosing to use that one to get metadata about the page
        try:
            self.file_metadata = client.databases.retrieve(
                database_id=self.database_id,
            )  # type: ignore
            self.check_exists = True
            self.file_exists = True
        except APIResponseError as error:
            if error.code == APIErrorCode.ObjectNotFound:
                self.check_exists = True
                self.file_exists = False
            else:
                self.config.get_logger().error(f"Error: {error}")

    @property
    def date_created(self) -> Optional[str]:
        """The date the document was created on the source system."""
        if not self.file_metadata:
            self.get_file_metadata()

        return self.file_metadata.created_time if self.file_metadata else None

    @property
    def date_modified(self) -> Optional[str]:
        """The date the document was last modified on the source system."""
        if not self.file_metadata:
            self.get_file_metadata()

        return self.file_metadata.last_edited_time if self.file_metadata else None

    @property
    def exists(self) -> Optional[bool]:
        """Whether the document exists on the remote source."""
        if self.check_exists:
            return self.file_exists

        self.get_file_metadata()

        return self.file_exists

    @property
    def filename(self):
        """The filename of the file created from a notion page"""
        return self._tmp_download_file()


@requires_dependencies(dependencies=["notion_client"])
class NotionConnector(ConnectorCleanupMixin, BaseConnector):
    """Objects of this class support fetching document(s) from"""

    config: SimpleNotionConfig

    def __init__(
        self,
        standard_config: StandardConnectorConfig,
        config: SimpleNotionConfig,
    ):
        super().__init__(
            standard_config=standard_config,
            config=config,
        )

    def initialize(self):
        """Verify that can get metadata for an object, validates connections info."""
        pass

    @requires_dependencies(dependencies=["notion_client"])
    def get_child_page_content(self, page_id: str):
        from unstructured.ingest.connector.notion.client import Client as NotionClient
        from unstructured.ingest.connector.notion.helpers import (
            get_recursive_content_from_page,
        )

        client = NotionClient(auth=self.config.api_key, logger=self.config.get_logger())

        child_content = get_recursive_content_from_page(
            client=client,
            page_id=page_id,
            logger=self.config.get_logger(),
        )
        return child_content

    def get_child_content(self, page_id: str):
        from unstructured.ingest.connector.notion.client import Client as NotionClient
        from unstructured.ingest.connector.notion.helpers import (
            get_recursive_content_from_page,
        )

        client = NotionClient(auth=self.config.api_key, logger=self.config.logger)

        child_content = get_recursive_content_from_page(
            client=client,
            page_id=page_id,
            logger=self.config.get_logger(),
        )
        return child_content

    @requires_dependencies(dependencies=["notion_client"])
    def get_child_database_content(self, database_id: str):
        from unstructured.ingest.connector.notion.client import Client as NotionClient
        from unstructured.ingest.connector.notion.helpers import (
            get_recursive_content_from_database,
        )

        client = NotionClient(auth=self.config.api_key, logger=self.config.get_logger())

        child_content = get_recursive_content_from_database(
            client=client,
            database_id=database_id,
            logger=self.config.get_logger(),
        )
        return child_content

    def get_ingest_docs(self):
        docs: List[BaseIngestDoc] = []
        if self.config.page_ids:
            docs += [
                NotionPageIngestDoc(
                    standard_config=self.standard_config,
                    config=self.config,
                    page_id=page_id,
                    api_key=self.config.api_key,
                )
                for page_id in self.config.page_ids
            ]
        if self.config.database_ids:
            docs += [
                NotionDatabaseIngestDoc(
                    standard_config=self.standard_config,
                    config=self.config,
                    database_id=database_id,
                    api_key=self.config.api_key,
                )
                for database_id in self.config.database_ids
            ]
        if self.config.recursive:
            child_pages = []
            child_databases = []
            for page_id in self.config.page_ids:
                child_content = self.get_child_page_content(page_id=page_id)
                child_pages.extend(child_content.child_pages)
                child_databases.extend(child_content.child_databases)

            for database_id in self.config.database_ids:
                child_content = self.get_child_database_content(database_id=database_id)
                child_pages.extend(child_content.child_pages)
                child_databases.extend(child_content.child_databases)

            # Remove duplicates
            child_pages = list(set(child_pages))
            child_pages = [c for c in child_pages if c not in self.config.page_ids]

            child_databases = list(set(child_databases))
            child_databases = [db for db in child_databases if db not in self.config.database_ids]

            if child_pages:
                self.config.get_logger().info(
                    "Adding the following child page ids: {}".format(", ".join(child_pages)),
                )
                docs += [
                    NotionPageIngestDoc(
                        standard_config=self.standard_config,
                        config=self.config,
                        page_id=page_id,
                        api_key=self.config.api_key,
                    )
                    for page_id in child_pages
                ]

            if child_databases:
                self.config.get_logger().info(
                    "Adding the following child database ids: {}".format(
                        ", ".join(child_databases),
                    ),
                )
                docs += [
                    NotionDatabaseIngestDoc(
                        standard_config=self.standard_config,
                        config=self.config,
                        database_id=database_id,
                        api_key=self.config.api_key,
                    )
                    for database_id in child_databases
                ]

        return docs
