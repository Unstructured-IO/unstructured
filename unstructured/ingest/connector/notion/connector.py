import typing as t
from dataclasses import dataclass, field
from pathlib import Path
from uuid import UUID

import httpx

from unstructured.ingest.enhanced_dataclass import enhanced_field
from unstructured.ingest.error import SourceConnectionError
from unstructured.ingest.interfaces import (
    AccessConfig,
    BaseConnectorConfig,
    BaseSingleIngestDoc,
    BaseSourceConnector,
    IngestDocCleanupMixin,
    RetryStrategyConfig,
    SourceConnectorCleanupMixin,
)
from unstructured.ingest.logger import logger
from unstructured.utils import (
    requires_dependencies,
)

NOTION_API_VERSION = "2022-06-28"
if t.TYPE_CHECKING:
    from unstructured.ingest.connector.notion.client import Client as NotionClient


@dataclass
class NotionAccessConfig(AccessConfig):
    notion_api_key: str = enhanced_field(sensitive=True)


@dataclass
class SimpleNotionConfig(BaseConnectorConfig):
    """Connector config to process all messages by channel id's."""

    access_config: NotionAccessConfig
    page_ids: t.Optional[t.List[str]] = None
    database_ids: t.Optional[t.List[str]] = None
    recursive: bool = False

    def __post_init__(self):
        if self.page_ids:
            self.page_ids = [str(UUID(p.strip())) for p in self.page_ids]

        if self.database_ids:
            self.database_ids = [str(UUID(d.strip())) for d in self.database_ids]


@dataclass
class NotionPageIngestDoc(IngestDocCleanupMixin, BaseSingleIngestDoc):
    """Class encapsulating fetching a doc and writing processed results (but not
    doing the processing!).

    Also includes a cleanup method. When things go wrong and the cleanup
    method is not called, the file is left behind on the filesystem to assist debugging.
    """

    page_id: str
    connector_config: SimpleNotionConfig
    registry_name: str = "notion_page"
    retry_strategy_config: t.Optional[RetryStrategyConfig] = None

    def _tmp_download_file(self):
        page_file = self.page_id + ".html"
        return Path(self.read_config.download_dir) / page_file

    @property
    def _output_filename(self):
        page_file = self.page_id + ".json"
        return Path(self.processor_config.output_dir) / page_file

    def _create_full_tmp_dir_path(self):
        self._tmp_download_file().parent.mkdir(parents=True, exist_ok=True)

    @requires_dependencies(dependencies=["notion_client"], extras="notion")
    def get_client(self):
        from unstructured.ingest.connector.notion.client import Client as NotionClient

        # Pin the version of the api to avoid schema changes
        return NotionClient(
            notion_version=NOTION_API_VERSION,
            auth=self.connector_config.access_config.notion_api_key,
            logger=logger,
            log_level=logger.level,
            retry_strategy_config=self.retry_strategy_config,
        )

    @BaseSingleIngestDoc.skip_if_file_exists
    @requires_dependencies(dependencies=["notion_client"], extras="notion")
    def get_file(self):
        from notion_client import APIErrorCode, APIResponseError

        from unstructured.ingest.connector.notion.helpers import extract_page_html

        self._create_full_tmp_dir_path()

        client = self.get_client()

        try:
            text_extraction = extract_page_html(
                client=client,
                page_id=self.page_id,
                logger=logger,
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
                logger.error(f"Error: {error}")

    @requires_dependencies(dependencies=["notion_client"], extras="notion")
    def get_file_metadata(self):
        from notion_client import APIErrorCode, APIResponseError

        client = self.get_client()

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
                logger.error(f"Error: {error}")

    @property
    def date_created(self) -> t.Optional[str]:
        """The date the document was created on the source system."""
        if not hasattr(self, "file_metadata") or not self.file_metadata:
            self.get_file_metadata()

        return self.file_metadata.created_time if self.file_metadata else None

    @property
    def date_modified(self) -> t.Optional[str]:
        """The date the document was last modified on the source system."""
        if not hasattr(self, "file_metadata") or not self.file_metadata:
            self.get_file_metadata()

        return self.file_metadata.last_edited_time if self.file_metadata else None

    @property
    def exists(self) -> t.Optional[bool]:
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
class NotionDatabaseIngestDoc(IngestDocCleanupMixin, BaseSingleIngestDoc):
    """Class encapsulating fetching a doc and writing processed results (but not
    doing the processing!).

    Also includes a cleanup method. When things go wrong and the cleanup
    method is not called, the file is left behind on the filesystem to assist debugging.
    """

    database_id: str
    connector_config: SimpleNotionConfig
    retry_strategy_config: t.Optional[RetryStrategyConfig] = None
    registry_name: str = "notion_database"

    def _tmp_download_file(self):
        page_file = self.database_id + ".html"
        return Path(self.read_config.download_dir) / page_file

    @property
    def _output_filename(self):
        page_file = self.database_id + ".json"
        return Path(self.processor_config.output_dir) / page_file

    def _create_full_tmp_dir_path(self):
        self._tmp_download_file().parent.mkdir(parents=True, exist_ok=True)

    @requires_dependencies(dependencies=["notion_client"], extras="notion")
    def get_client(self):
        from unstructured.ingest.connector.notion.client import Client as NotionClient

        # Pin the version of the api to avoid schema changes
        return NotionClient(
            notion_version=NOTION_API_VERSION,
            auth=self.connector_config.access_config.notion_api_key,
            logger=logger,
            log_level=logger.level,
            retry_strategy_config=self.retry_strategy_config,
        )

    @BaseSingleIngestDoc.skip_if_file_exists
    @requires_dependencies(dependencies=["notion_client"], extras="notion")
    def get_file(self):
        from notion_client import APIErrorCode, APIResponseError

        from unstructured.ingest.connector.notion.helpers import extract_database_html

        self._create_full_tmp_dir_path()

        client = self.get_client()

        try:
            text_extraction = extract_database_html(
                client=client,
                database_id=self.database_id,
                logger=logger,
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
                logger.error(f"Error: {error}")

    @requires_dependencies(dependencies=["notion_client"], extras="notion")
    def get_file_metadata(self):
        from notion_client import APIErrorCode, APIResponseError

        client = self.get_client()

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
                logger.error(f"Error: {error}")

    @property
    def date_created(self) -> t.Optional[str]:
        """The date the document was created on the source system."""
        if not hasattr(self, "file_metadata") or not self.file_metadata:
            self.get_file_metadata()

        return self.file_metadata.created_time if self.file_metadata else None

    @property
    def date_modified(self) -> t.Optional[str]:
        """The date the document was last modified on the source system."""
        if not hasattr(self, "file_metadata") or not self.file_metadata:
            self.get_file_metadata()

        return self.file_metadata.last_edited_time if self.file_metadata else None

    @property
    def exists(self) -> t.Optional[bool]:
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
class NotionSourceConnector(SourceConnectorCleanupMixin, BaseSourceConnector):
    """Objects of this class support fetching document(s) from"""

    connector_config: SimpleNotionConfig
    retry_strategy_config: t.Optional[RetryStrategyConfig] = None
    _client: t.Optional["NotionClient"] = field(init=False, default=None)

    @property
    def client(self) -> "NotionClient":
        if self._client is None:
            self._client = self.create_client()
        return self._client

    @requires_dependencies(dependencies=["notion_client"], extras="notion")
    def create_client(self) -> "NotionClient":
        from unstructured.ingest.connector.notion.client import Client as NotionClient

        return NotionClient(
            notion_version=NOTION_API_VERSION,
            auth=self.connector_config.access_config.notion_api_key,
            logger=logger,
            log_level=logger.level,
            retry_strategy_config=self.retry_strategy_config,
        )

    def check_connection(self):
        try:
            request = self.client._build_request("HEAD", "users")
            response = self.client.client.send(request)
            response.raise_for_status()
        except httpx.HTTPStatusError as http_error:
            logger.error(f"failed to validate connection: {http_error}", exc_info=True)
            raise SourceConnectionError(f"failed to validate connection: {http_error}")

    @requires_dependencies(dependencies=["notion_client"], extras="notion")
    def initialize(self):
        """Verify that can get metadata for an object, validates connections info."""
        _ = self.client

    @requires_dependencies(dependencies=["notion_client"], extras="notion")
    def get_child_page_content(self, page_id: str):
        from unstructured.ingest.connector.notion.helpers import (
            get_recursive_content_from_page,
        )

        # sanity check that database id is valid
        resp_code = self.client.pages.retrieve_status(page_id=page_id)
        if resp_code != 200:
            raise ValueError(
                f"page associated with page id could not be found: {page_id}",
            )

        child_content = get_recursive_content_from_page(
            client=self.client,
            page_id=page_id,
            logger=logger,
        )
        return child_content

    def get_child_content(self, page_id: str):
        from unstructured.ingest.connector.notion.helpers import (
            get_recursive_content_from_page,
        )

        child_content = get_recursive_content_from_page(
            client=self.client,
            page_id=page_id,
            logger=logger,
        )
        return child_content

    @requires_dependencies(dependencies=["notion_client"], extras="notion")
    def get_child_database_content(self, database_id: str):
        from unstructured.ingest.connector.notion.helpers import (
            get_recursive_content_from_database,
        )

        # sanity check that database id is valid
        resp_code = self.client.databases.retrieve_status(database_id=database_id)
        if resp_code != 200:
            raise ValueError(
                f"database associated with database id could not be found: {database_id}",
            )

        child_content = get_recursive_content_from_database(
            client=self.client,
            database_id=database_id,
            logger=logger,
        )
        return child_content

    def get_ingest_docs(self):
        docs: t.List[BaseSingleIngestDoc] = []
        if self.connector_config.page_ids:
            docs += [
                NotionPageIngestDoc(
                    connector_config=self.connector_config,
                    processor_config=self.processor_config,
                    retry_strategy_config=self.retry_strategy_config,
                    read_config=self.read_config,
                    page_id=page_id,
                )
                for page_id in self.connector_config.page_ids
            ]
        if self.connector_config.database_ids:
            docs += [
                NotionDatabaseIngestDoc(
                    connector_config=self.connector_config,
                    processor_config=self.processor_config,
                    retry_strategy_config=self.retry_strategy_config,
                    read_config=self.read_config,
                    database_id=database_id,
                )
                for database_id in self.connector_config.database_ids
            ]
        if self.connector_config.recursive:
            logger.info("Getting recursive content")
            child_pages = []
            child_databases = []
            if self.connector_config.page_ids:
                for page_id in self.connector_config.page_ids:
                    child_content = self.get_child_page_content(page_id=page_id)
                    child_pages.extend(child_content.child_pages)
                    child_databases.extend(child_content.child_databases)

            if self.connector_config.database_ids:
                for database_id in self.connector_config.database_ids:
                    child_content = self.get_child_database_content(database_id=database_id)
                    child_pages.extend(child_content.child_pages)
                    child_databases.extend(child_content.child_databases)

            # Remove duplicates
            child_pages = list(set(child_pages))
            if self.connector_config.page_ids:
                child_pages = [c for c in child_pages if c not in self.connector_config.page_ids]

            child_databases = list(set(child_databases))
            if self.connector_config.database_ids:
                child_databases = [
                    db for db in child_databases if db not in self.connector_config.database_ids
                ]

            if child_pages:
                logger.info(
                    "Adding the following child page ids: {}".format(", ".join(child_pages)),
                )
                docs += [
                    NotionPageIngestDoc(
                        connector_config=self.connector_config,
                        processor_config=self.processor_config,
                        retry_strategy_config=self.retry_strategy_config,
                        read_config=self.read_config,
                        page_id=page_id,
                    )
                    for page_id in child_pages
                ]

            if child_databases:
                logger.info(
                    "Adding the following child database ids: {}".format(
                        ", ".join(child_databases),
                    ),
                )
                docs += [
                    NotionDatabaseIngestDoc(
                        connector_config=self.connector_config,
                        processor_config=self.processor_config,
                        retry_strategy_config=self.retry_strategy_config,
                        read_config=self.read_config,
                        database_id=database_id,
                    )
                    for database_id in child_databases
                ]

        return docs
