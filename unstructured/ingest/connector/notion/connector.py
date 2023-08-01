import json
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from unstructured.ingest.interfaces import (
    BaseConnector,
    BaseConnectorConfig,
    BaseIngestDoc,
    ConnectorCleanupMixin,
    IngestDocCleanupMixin,
    StandardConnectorConfig,
)
from unstructured.utils import (
    requires_dependencies,
)

# https://developers.notion.com/reference/block
notion_block_types = [
    "bookmark",
    "breadcrumb",
    "bulleted_list_item",
    "callout",
    "child_database",
    "child_page",
    "column",
    "column_list",
    "divider",
    "embed",
    "equation",
    "file",
    "heading_1",
    "heading_2",
    "heading_3",
    "image",
    "link_preview",
    "link_to_page",
    "numbered_list_item",
    "paragraph",
    "pdf",
    "quote",
    "synced_block",
    "table",
    "table_of_contents",
    "table_row",
    "template",
    "to_do",
    "toggle",
    "unsupported",
    "video",
]


@dataclass
class SimpleNotionConfig(BaseConnectorConfig):
    """Connector config to process all messages by channel id's."""

    page_ids: List[str]
    api_key: str
    logger: logging.Logger

    @staticmethod
    def parse_page_ids(page_ids_str: str) -> List[str]:
        """Parses a comma separated list of page ids into a list."""
        return [x.strip() for x in page_ids_str.split(",")]


@dataclass
class NotionIngestDoc(IngestDocCleanupMixin, BaseIngestDoc):
    """Class encapsulating fetching a doc and writing processed results (but not
    doing the processing!).

    Also includes a cleanup method. When things go wrong and the cleanup
    method is not called, the file is left behind on the filesystem to assist debugging.
    """

    page_id: str
    api_key: str
    config: SimpleNotionConfig
    file_metadata: dict = field(default_factory=dict)
    file_exists: bool = False
    check_exists: bool = False

    def _tmp_download_file(self):
        page_file = self.page_id + ".json"
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
        from notion_client import Client as NotionClient
        from notion_client.api_endpoints import BlocksChildrenEndpoint
        from notion_client.helpers import iterate_paginated_api

        self._create_full_tmp_dir_path()

        self.config.logger.debug(f"fetching page {self.page_id} - PID: {os.getpid()}")

        client = NotionClient(auth=self.api_key, logger=self.config.logger)

        try:
            content = {}
            child_endpoint = BlocksChildrenEndpoint(client)
            pages_w_child = [self.page_id]
            pages_processed = []
            while len(pages_w_child) > 0:
                parent_id = pages_w_child.pop()
                for children in iterate_paginated_api(child_endpoint.list, block_id=parent_id):
                    for c in children:
                        child_id = c["id"]
                        content[child_id] = c
                        if (
                            c["has_children"]
                            and child_id not in pages_processed
                            and child_id not in pages_w_child
                            and child_id != parent_id
                        ):
                            self.config.logger.debug(
                                f"Adding child to process for more children: {child_id}",
                            )
                            pages_w_child.append(c["id"])
                pages_processed.append(parent_id)
            self.check_exists = True
            self.file_exists = True
            with open(self._tmp_download_file(), "w") as page_file:
                json.dump(content, page_file)
        except APIResponseError as error:
            if error.code == APIErrorCode.ObjectNotFound:
                self.check_exists = True
                self.file_exists = False
            else:
                self.config.logger.error(f"Error: {error}")

    @requires_dependencies(dependencies=["notion_client"])
    def get_file_metadata(self):
        from notion_client import APIErrorCode, APIResponseError
        from notion_client import Client as NotionClient

        client = NotionClient(auth=self.api_key, logger=self.config.logger)

        # The Notion block endpoint gives more hierarchical information (parent,child relationships)
        # than the pages endpoint so choosing to use that one to get metadata about the page
        try:
            self.file_metadata: dict = client.blocks.retrieve(block_id=self.page_id)  # type: ignore
            self.check_exists = True
            self.file_exists = True
        except APIResponseError as error:
            if error.code == APIErrorCode.ObjectNotFound:
                self.check_exists = True
                self.file_exists = False
            else:
                self.config.logger.error(f"Error: {error}")

    @property
    def date_created(self) -> Optional[str]:
        """The date the document was created on the source system."""
        if not self.file_metadata:
            self.get_file_metadata()

        return self.file_metadata["created_time"]

    @property
    def date_modified(self) -> Optional[str]:
        """The date the document was last modified on the source system."""
        if not self.file_metadata:
            self.get_file_metadata()

        return self.file_metadata["last_edited_time"]

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

    def __init__(self, standard_config: StandardConnectorConfig, config: SimpleNotionConfig):
        super().__init__(standard_config, config)

    def initialize(self):
        """Verify that can get metadata for an object, validates connections info."""
        pass

    def get_ingest_docs(self):
        return [
            NotionIngestDoc(
                standard_config=self.standard_config,
                config=self.config,
                page_id=page_id,
                api_key=self.config.api_key,
            )
            for page_id in self.config.page_ids
        ]
