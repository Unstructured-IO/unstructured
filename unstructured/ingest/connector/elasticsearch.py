import hashlib
import json
import os
import typing as t
from dataclasses import dataclass
from pathlib import Path

from unstructured.ingest.error import SourceConnectionError
from unstructured.ingest.interfaces import (
    BaseConnectorConfig,
    BaseIngestDoc,
    BaseSourceConnector,
    IngestDocCleanupMixin,
    SourceConnectorCleanupMixin,
    SourceMetadata,
)
from unstructured.ingest.logger import logger
from unstructured.utils import requires_dependencies


@dataclass
class SimpleElasticsearchConfig(BaseConnectorConfig):
    """Connector config where:
    url is the url to access the elasticsearch server,
    index_name is the name of the index to reach to,

    and jq_query is a query to get specific fields from each document that is reached,
    rather than getting and processing all fields in a document.
    """

    url: str
    index_name: str
    jq_query: t.Optional[str]


@dataclass
class ElasticsearchDocumentMeta:
    """Metadata specifying:
    name of the elasticsearch index that is being reached to,
    and the id of document that is being reached to,
    """

    index_name: str
    document_id: str


@dataclass
class ElasticsearchIngestDoc(IngestDocCleanupMixin, BaseIngestDoc):
    """Class encapsulating fetching a doc and writing processed results (but not
    doing the processing!).

    Current implementation creates a python Elasticsearch client to fetch each doc,
    rather than creating a client for each thread.
    """

    connector_config: SimpleElasticsearchConfig
    document_meta: ElasticsearchDocumentMeta
    registry_name: str = "elasticsearch"

    # TODO: remove one of filename or _tmp_download_file, using a wrapper
    @property
    def filename(self):
        return (
            Path(self.read_config.download_dir)
            / self.document_meta.index_name
            / f"{self.document_meta.document_id}.txt"
        ).resolve()

    @property
    def _output_filename(self):
        """Create filename document id combined with a hash of the query to uniquely identify
        the output file."""
        # Generate SHA256 hash and take the first 8 characters
        query_hash = hashlib.sha256((self.connector_config.jq_query or "").encode()).hexdigest()[:8]
        output_file = f"{self.document_meta.document_id}-{query_hash}.json"
        return (
            Path(self.processor_config.output_dir) / self.connector_config.index_name / output_file
        )

    # TODO: change test fixtures such that examples with
    # nested dictionaries are included in test documents
    def _flatten_values(self, value, seperator="\n", no_value_str=""):
        """Flattens list or dict objects. Joins each value or item with
        the seperator character. Keys are not included in the joined string.
        When a dict value or a list item is None, no_value_str is used to
        represent that value / item."""
        if value is None:
            return no_value_str

        if isinstance(value, list):
            flattened_values = [self._flatten_values(item, seperator) for item in value]
            return seperator.join(flattened_values)

        elif isinstance(value, dict):
            flattened_values = [self._flatten_values(item, seperator) for item in value.values()]
            return seperator.join(flattened_values)

        else:
            return str(value)

    def _concatenate_dict_fields(self, dictionary, seperator="\n"):
        """Concatenates all values for each key in a dictionary in a nested manner.
        Used to parse a python dictionary to an aggregated string"""
        values = [self._flatten_values(value, seperator) for value in dictionary.values()]
        concatenated_values = seperator.join(values)
        return concatenated_values

    @requires_dependencies(["elasticsearch"], extras="elasticsearch")
    def _get_document(self):
        from elasticsearch import Elasticsearch, NotFoundError

        try:
            # TODO: instead of having a separate client for each doc,
            # have a separate client for each process
            es = Elasticsearch(self.connector_config.url)
            document = es.get(
                index=self.connector_config.index_name,
                id=self.document_meta.document_id,
            )
        except NotFoundError:
            logger.error("Couldn't find document with ID: %s", self.document_meta.document_id)
            return None
        return document

    def update_source_metadata(self, **kwargs):
        document = kwargs.get("document", self._get_document())
        if document is None:
            self.source_metadata = SourceMetadata(
                exists=False,
            )
            return
        self.source_metadata = SourceMetadata(
            version=document["_version"],
            exists=document["found"],
        )

    @SourceConnectionError.wrap
    @requires_dependencies(["jq"], extras="elasticsearch")
    @BaseIngestDoc.skip_if_file_exists
    def get_file(self):
        import jq

        logger.debug(f"Fetching {self} - PID: {os.getpid()}")
        document = self._get_document()
        self.update_source_metadata(document=document)
        if document is None:
            raise ValueError(
                f"Failed to get document {self.document_meta.document_id}",
            )

        document_dict = document.body["_source"]
        if self.connector_config.jq_query:
            document_dict = json.loads(
                jq.compile(self.connector_config.jq_query).input(document_dict).text(),
            )
        self.document = self._concatenate_dict_fields(document_dict)
        self.filename.parent.mkdir(parents=True, exist_ok=True)
        with open(self.filename, "w", encoding="utf8") as f:
            f.write(self.document)

    @property
    def date_created(self) -> t.Optional[str]:
        return None

    @property
    def date_modified(self) -> t.Optional[str]:
        return None

    @property
    def source_url(self) -> t.Optional[str]:
        return None

    @property
    def record_locator(self) -> t.Optional[t.Dict[str, t.Any]]:
        return {
            "url": self.connector_config.url,
            "index_name": self.connector_config.index_name,
            "document_id": self.document_meta.document_id,
        }


@dataclass
class ElasticsearchSourceConnector(SourceConnectorCleanupMixin, BaseSourceConnector):
    """Fetches particular fields from all documents in a given elasticsearch cluster and index"""

    connector_config: SimpleElasticsearchConfig

    @requires_dependencies(["elasticsearch"], extras="elasticsearch")
    def initialize(self):
        from elasticsearch import Elasticsearch

        self.es = Elasticsearch(self.connector_config.url)
        self.scan_query: dict = {"query": {"match_all": {}}}
        self.search_query: dict = {"match_all": {}}
        self.es.search(index=self.connector_config.index_name, query=self.search_query, size=1)

    @requires_dependencies(["elasticsearch"], extras="elasticsearch")
    def _get_doc_ids(self):
        """Fetches all document ids in an index"""
        from elasticsearch.helpers import scan

        hits = scan(
            self.es,
            query=self.scan_query,
            scroll="1m",
            index=self.connector_config.index_name,
        )

        return [hit["_id"] for hit in hits]

    def get_ingest_docs(self):
        """Fetches all documents in an index, using ids that are fetched with _get_doc_ids"""
        ids = self._get_doc_ids()
        return [
            ElasticsearchIngestDoc(
                connector_config=self.connector_config,
                processor_config=self.processor_config,
                read_config=self.read_config,
                document_meta=ElasticsearchDocumentMeta(self.connector_config.index_name, id),
            )
            for id in ids
        ]
