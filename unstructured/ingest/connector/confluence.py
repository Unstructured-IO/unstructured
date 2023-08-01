import math
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from atlassian import Confluence

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


@dataclass
class SimpleConfluenceConfig(BaseConnectorConfig):
    """Connector config where:
    user_email is the email to authenticate into Confluence Cloud,
    api_token is the api token to authenticate into Confluence Cloud,
    and url is the URL pointing to the Confluence Cloud instance.

    Check https://developer.atlassian.com/cloud/confluence/basic-auth-for-rest-apis/
    for more info on the api_token.
    """

    user_email: str
    api_token: str
    url: str
    list_of_spaces: Optional[str]
    max_number_of_spaces: int
    max_number_of_docs_from_each_space: int


@dataclass
class ConfluenceFileMeta:
    """Metadata specifying:
    id for the confluence space that the document locates in,
    and the id of document that is being reached to.
    """

    space_id: str
    document_id: str


def scroll_wrapper(func):
    def wrapper(*args, **kwargs):
        """Wraps a function to obtain scroll functionality."""
        number_of_items_to_fetch = kwargs["number_of_items_to_fetch"]
        del kwargs["number_of_items_to_fetch"]

        kwargs["limit"] = min(100, number_of_items_to_fetch)
        kwargs["start"] = 0 if "start" not in kwargs else kwargs["start"]

        all_results = []
        num_iterations = math.ceil(number_of_items_to_fetch / kwargs["limit"])

        for _ in range(num_iterations):
            response = func(*args, **kwargs)
            if type(response) is list:
                all_results += func(*args, **kwargs)
            elif type(response) is dict:
                all_results += func(*args, **kwargs)["results"]

            kwargs["start"] += kwargs["limit"]

        return all_results[:number_of_items_to_fetch]

    return wrapper


@dataclass
class ConfluenceIngestDoc(IngestDocCleanupMixin, BaseIngestDoc):
    """Class encapsulating fetching a doc and writing processed results (but not
    doing the processing).

    Current implementation creates a Confluence connection object
    to fetch each doc, rather than creating a it for each thread.
    """

    config: SimpleConfluenceConfig
    file_meta: ConfluenceFileMeta

    # TODO: remove one of filename or _tmp_download_file, using a wrapper
    @property
    def filename(self):
        return (
            Path(self.standard_config.download_dir)
            / self.file_meta.space_id
            / f"{self.file_meta.document_id}.html"
        ).resolve()

    @property
    def _output_filename(self):
        """Create output file path based on output directory, space id and document id."""
        output_file = f"{self.file_meta.document_id}.json"
        return Path(self.standard_config.output_dir) / self.file_meta.space_id / output_file

    @requires_dependencies(["atlassian"])
    @BaseIngestDoc.skip_if_file_exists
    def get_file(self):
        logger.debug(f"Fetching {self} - PID: {os.getpid()}")

        # TODO: instead of having a separate connection object for each doc,
        # have a separate connection object for each process
        confluence = Confluence(
            self.config.url,
            username=self.config.user_email,
            password=self.config.api_token,
        )

        result = confluence.get_page_by_id(page_id=self.file_meta.document_id, expand="body.view")
        self.document = result["body"]["view"]["value"]
        self.filename.parent.mkdir(parents=True, exist_ok=True)
        with open(self.filename, "w", encoding="utf8") as f:
            f.write(self.document)


@requires_dependencies(["atlassian"])
@dataclass
class ConfluenceConnector(ConnectorCleanupMixin, BaseConnector):
    """Fetches body fields from all documents within all spaces in a Confluence Cloud instance."""

    config: SimpleConfluenceConfig

    def __init__(
        self,
        standard_config: StandardConnectorConfig,
        config: SimpleConfluenceConfig,
    ):
        super().__init__(standard_config, config)

    @requires_dependencies(["atlassian"])
    def initialize(self):
        self.confluence = Confluence(
            url=self.config.url,
            username=self.config.user_email,
            password=self.config.api_token,
        )

        self.list_of_spaces = None
        if self.config.list_of_spaces:
            self.list_of_spaces = self.config.list_of_spaces.split(",")
            if self.config.max_number_of_spaces:
                logger.warning(
                    """--confluence-list-of-spaces and --confluence-num-of-spaces cannot
                    be used at the same time. Connector will only fetch the
                    --confluence-list-of-spaces that you've provided.""",
                )

    @requires_dependencies(["atlassian"])
    def _get_space_ids(self):
        """Fetches spaces in a confluence domain."""

        get_spaces_with_scroll = scroll_wrapper(self.confluence.get_all_spaces)

        all_results = get_spaces_with_scroll(
            number_of_items_to_fetch=self.config.max_number_of_spaces,
        )

        space_ids = [space["key"] for space in all_results]
        return space_ids

    @requires_dependencies(["atlassian"])
    def _get_docs_ids_within_one_space(
        self,
        space_id: str,
        content_type: str = "page",
    ):
        get_pages_with_scroll = scroll_wrapper(self.confluence.get_all_pages_from_space)
        results = get_pages_with_scroll(
            space=space_id,
            number_of_items_to_fetch=self.config.max_number_of_docs_from_each_space,
            content_type=content_type,
        )

        doc_ids = [(space_id, doc["id"]) for doc in results]
        return doc_ids

    @requires_dependencies(["atlassian"])
    def _get_doc_ids_within_spaces(self):
        space_ids = self._get_space_ids() if not self.list_of_spaces else self.list_of_spaces

        doc_ids_all = [self._get_docs_ids_within_one_space(space_id=id) for id in space_ids]

        doc_ids_flattened = [
            (space_id, doc_id)
            for doc_ids_space in doc_ids_all
            for space_id, doc_id in doc_ids_space
        ]
        return doc_ids_flattened

    def get_ingest_docs(self):
        """Fetches all documents in a confluence space."""
        doc_ids = self._get_doc_ids_within_spaces()
        return [
            ConfluenceIngestDoc(
                self.standard_config,
                self.config,
                ConfluenceFileMeta(space_id, doc_id),
            )
            for space_id, doc_id in doc_ids
        ]
