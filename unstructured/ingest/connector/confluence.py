import math
import os
import typing as t
from dataclasses import dataclass, field
from pathlib import Path

from unstructured.ingest.error import SourceConnectionError
from unstructured.ingest.interfaces import (
    BaseConnectorConfig,
    BaseIngestDoc,
    BaseSourceConnector,
    IngestDocCleanupMixin,
    SourceConnectorCleanupMixin,
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
    max_number_of_spaces: int
    max_number_of_docs_from_each_space: int
    spaces: t.List[str] = field(default_factory=list)


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

    connector_config: SimpleConfluenceConfig
    file_meta: ConfluenceFileMeta
    registry_name: str = "confluence"

    # TODO: remove one of filename or _tmp_download_file, using a wrapper
    @property
    def filename(self):
        if not self.read_config.download_dir:
            return None
        return (
            Path(self.read_config.download_dir)
            / self.file_meta.space_id
            / f"{self.file_meta.document_id}.html"
        ).resolve()

    @property
    def _output_filename(self):
        """Create output file path based on output directory, space id and document id."""
        output_file = f"{self.file_meta.document_id}.json"
        return Path(self.partition_config.output_dir) / self.file_meta.space_id / output_file

    @SourceConnectionError.wrap
    @requires_dependencies(["atlassian"], extras="confluence")
    @BaseIngestDoc.skip_if_file_exists
    def get_file(self):
        from atlassian import Confluence

        logger.debug(f"Fetching {self} - PID: {os.getpid()}")

        # TODO: instead of having a separate connection object for each doc,
        # have a separate connection object for each process
        confluence = Confluence(
            self.connector_config.url,
            username=self.connector_config.user_email,
            password=self.connector_config.api_token,
        )

        result = confluence.get_page_by_id(page_id=self.file_meta.document_id, expand="body.view")
        self.document = result["body"]["view"]["value"]
        self.filename.parent.mkdir(parents=True, exist_ok=True)
        with open(self.filename, "w", encoding="utf8") as f:
            f.write(self.document)


@dataclass
class ConfluenceSourceConnector(SourceConnectorCleanupMixin, BaseSourceConnector):
    """Fetches body fields from all documents within all spaces in a Confluence Cloud instance."""

    connector_config: SimpleConfluenceConfig

    @requires_dependencies(["atlassian"], extras="Confluence")
    def initialize(self):
        from atlassian import Confluence

        self.confluence = Confluence(
            url=self.connector_config.url,
            username=self.connector_config.user_email,
            password=self.connector_config.api_token,
        )

        self.list_of_spaces = None
        if self.connector_config.spaces:
            self.list_of_spaces = self.connector_config.spaces
            if self.connector_config.max_number_of_spaces:
                logger.warning(
                    """--confluence-list-of-spaces and --confluence-num-of-spaces cannot
                    be used at the same time. Connector will only fetch the
                    --confluence-list-of-spaces that you've provided.""",
                )

    @requires_dependencies(["atlassian"], extras="Confluence")
    def _get_space_ids(self):
        """Fetches spaces in a confluence domain."""

        get_spaces_with_scroll = scroll_wrapper(self.confluence.get_all_spaces)

        all_results = get_spaces_with_scroll(
            number_of_items_to_fetch=self.connector_config.max_number_of_spaces,
        )

        space_ids = [space["key"] for space in all_results]
        return space_ids

    @requires_dependencies(["atlassian"], extras="Confluence")
    def _get_docs_ids_within_one_space(
        self,
        space_id: str,
        content_type: str = "page",
    ):
        get_pages_with_scroll = scroll_wrapper(self.confluence.get_all_pages_from_space)
        results = get_pages_with_scroll(
            space=space_id,
            number_of_items_to_fetch=self.connector_config.max_number_of_docs_from_each_space,
            content_type=content_type,
        )

        doc_ids = [(space_id, doc["id"]) for doc in results]
        return doc_ids

    @requires_dependencies(["atlassian"], extras="Confluence")
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
                connector_config=self.connector_config,
                partition_config=self.partition_config,
                read_config=self.read_config,
                file_meta=ConfluenceFileMeta(space_id, doc_id),
            )
            for space_id, doc_id in doc_ids
        ]
