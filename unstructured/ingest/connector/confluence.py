import math
import os
import typing as t
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import requests

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

if t.TYPE_CHECKING:
    from atlassian import Confluence


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
class ConfluenceDocumentMeta:
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
            if isinstance(response, list):
                all_results += func(*args, **kwargs)
            elif isinstance(response, dict):
                all_results += func(*args, **kwargs)["results"]

            kwargs["start"] += kwargs["limit"]

        return all_results[:number_of_items_to_fetch]

    return wrapper


@dataclass
class ConfluenceIngestDoc(IngestDocCleanupMixin, BaseSingleIngestDoc):
    """Class encapsulating fetching a doc and writing processed results (but not
    doing the processing).

    Current implementation creates a Confluence connection object
    to fetch each doc, rather than creating a it for each thread.
    """

    connector_config: SimpleConfluenceConfig
    document_meta: ConfluenceDocumentMeta
    registry_name: str = "confluence"

    # TODO: remove one of filename or _tmp_download_file, using a wrapper
    @property
    def filename(self):
        if not self.read_config.download_dir:
            return None
        return (
            Path(self.read_config.download_dir)
            / self.document_meta.space_id
            / f"{self.document_meta.document_id}.html"
        ).resolve()

    @property
    def _output_filename(self):
        """Create output file path based on output directory, space id and document id."""
        output_file = f"{self.document_meta.document_id}.json"
        return Path(self.processor_config.output_dir) / self.document_meta.space_id / output_file

    @property
    def record_locator(self) -> t.Optional[t.Dict[str, t.Any]]:
        return {
            "url": self.connector_config.url,
            "page_id": self.document_meta.document_id,
        }

    @SourceConnectionNetworkError.wrap
    @requires_dependencies(["atlassian"], extras="Confluence")
    def _get_page(self):
        from atlassian import Confluence
        from atlassian.errors import ApiError

        try:
            confluence = Confluence(
                self.connector_config.url,
                username=self.connector_config.user_email,
                password=self.connector_config.api_token,
            )
            result = confluence.get_page_by_id(
                page_id=self.document_meta.document_id,
                expand="history.lastUpdated,version,body.view",
            )
        except ApiError as e:
            logger.error(e)
            return None
        return result

    def update_source_metadata(self, **kwargs):
        """Fetches file metadata from the current page."""
        page = kwargs.get("page", self._get_page())
        if page is None:
            self.source_metadata = SourceMetadata(
                exists=False,
            )
            return
        document_history = page["history"]
        date_created = datetime.strptime(
            document_history["createdDate"],
            "%Y-%m-%dT%H:%M:%S.%fZ",
        ).isoformat()
        if last_updated := document_history.get("lastUpdated", {}).get("when", ""):
            date_modified = datetime.strptime(
                last_updated,
                "%Y-%m-%dT%H:%M:%S.%fZ",
            ).isoformat()
        else:
            date_modified = date_created
        version = page["version"]["number"]
        self.source_metadata = SourceMetadata(
            date_created=date_created,
            date_modified=date_modified,
            version=version,
            source_url=page["_links"].get("self", None),
            exists=True,
        )

    @SourceConnectionError.wrap
    @requires_dependencies(["atlassian"], extras="confluence")
    @BaseSingleIngestDoc.skip_if_file_exists
    def get_file(self):
        logger.debug(f"Fetching {self} - PID: {os.getpid()}")

        # TODO: instead of having a separate connection object for each doc,
        # have a separate connection object for each process

        result = self._get_page()
        self.update_source_metadata(page=result)
        if result is None:
            raise ValueError(f"Failed to retrieve page with ID {self.document_meta.document_id}")
        self.document = result["body"]["view"]["value"]
        self.filename.parent.mkdir(parents=True, exist_ok=True)
        with open(self.filename, "w", encoding="utf8") as f:
            f.write(self.document)


@dataclass
class ConfluenceSourceConnector(SourceConnectorCleanupMixin, BaseSourceConnector):
    """Fetches body fields from all documents within all spaces in a Confluence Cloud instance."""

    connector_config: SimpleConfluenceConfig
    _confluence: t.Optional["Confluence"] = field(init=False, default=None)

    @property
    def confluence(self) -> "Confluence":
        from atlassian import Confluence

        if self._confluence is None:
            self._confluence = Confluence(
                url=self.connector_config.url,
                username=self.connector_config.user_email,
                password=self.connector_config.api_token,
            )
        return self._confluence

    @requires_dependencies(["atlassian"], extras="Confluence")
    def check_connection(self):
        url = "rest/api/space"
        try:
            self.confluence.request(method="HEAD", path=url)
        except requests.HTTPError as http_error:
            logger.error(f"failed to validate connection: {http_error}", exc_info=True)
            raise SourceConnectionError(f"failed to validate connection: {http_error}")

    @requires_dependencies(["atlassian"], extras="Confluence")
    def initialize(self):
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
                processor_config=self.processor_config,
                read_config=self.read_config,
                document_meta=ConfluenceDocumentMeta(space_id, doc_id),
            )
            for space_id, doc_id in doc_ids
        ]
