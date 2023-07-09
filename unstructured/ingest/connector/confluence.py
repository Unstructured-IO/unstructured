import os
from dataclasses import dataclass
from pathlib import Path

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


@dataclass
class ConfluenceFileMeta:
    """Metadata specifying:
    id for the confluence space that the document locates in,
    and the id of document that is being reached to.
    """

    space_id: str
    document_id: str


@dataclass
class ConfluenceIngestDoc(IngestDocCleanupMixin, BaseIngestDoc):
    # TODO: update docstring
    """Class encapsulating fetching a doc and writing processed results (but not
    doing the processing!).

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
            / f"{self.file_meta.document_id}.txt"
        ).resolve()

    @property
    def _output_filename(self):
        """Create output file path based on output directory, space id and document id"""
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
    """Fetches the body field from all documents from all spaces in a Confluence Cloud instance."""

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

        # TODO: should we put this as a connection-check?
        # try:
        # confluence.get_all_spaces(start=0, limit=1, expand=None)
        # except: ...

    @requires_dependencies(["atlassian"])
    def _get_all_space_ids(self, start: int = 0, limit: int = 500, expand=None):
        """Fetches all spaces in a confluence domain"""
        results = self.confluence.get_all_spaces(start=start, limit=limit, expand=expand)
        space_ids = [space["key"] for space in results["results"]]
        return space_ids

    @requires_dependencies(["atlassian"])
    def _get_all_docs_ids_in_space(
        self,
        space_id: str,
        start: int = 0,
        limit: int = 100,
        status=None,
        expand=None,
        content_type: str = "page",
    ):
        results = self.confluence.get_all_pages_from_space(
            space_id,
            start=start,
            limit=limit,
            status=status,
            expand=expand,
            content_type=content_type,
        )
        doc_ids = [(space_id, doc["id"]) for doc in results]
        return doc_ids

    @requires_dependencies(["atlassian"])
    def _get_all_doc_ids_in_all_spaces(self):
        space_ids = self._get_all_space_ids()
        doc_ids_all = [self._get_all_docs_ids_in_space(space_id) for space_id in space_ids]
        doc_ids_flattened = [
            (space_id, doc_id)
            for doc_ids_space in doc_ids_all
            for space_id, doc_id in doc_ids_space
        ]
        return doc_ids_flattened

    # TODO: different document subset selection options:
    # 1-get all docs in all spaces
    # 2-get all docs in just one space
    # 3-get some docs using a list of (space name | id) pairs

    # TODO for version 2: processing comments, images, doctext
    def get_ingest_docs(self):
        """Fetches all documents in a confluence space"""
        doc_ids = self._get_all_doc_ids_in_all_spaces()
        return [
            ConfluenceIngestDoc(
                self.standard_config,
                self.config,
                ConfluenceFileMeta(space_id, doc_id),
            )
            for space_id, doc_id in doc_ids
        ]
