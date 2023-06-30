import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import jq
from elasticsearch import Elasticsearch
from elasticsearch.helpers import scan

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
class SimpleElasticsearchConfig(BaseConnectorConfig):
    """Connector config where:
    url is the url to access the elasticsearch server,
    index_name is the name of the index to reach to,

    and jq_query is a query to get specific fields from each document that is reached,
    rather than getting and processing all fields in a document.
    """

    url: str
    index_name: str
    jq_query: Optional[str]


@dataclass
class ElasticsearchFileMeta:
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

    config: SimpleElasticsearchConfig
    file_meta: ElasticsearchFileMeta

    # TODO: remove one of filename or _tmp_download_file, using a wrapper
    @property
    def filename(self):
        return (
            Path(self.standard_config.download_dir)
            / self.file_meta.index_name
            / f"{self.file_meta.document_id}.txt"
        ).resolve()

    def _tmp_download_file(self):
        return (
            Path(self.standard_config.download_dir)
            / self.file_meta.index_name
            / f"{self.file_meta.document_id}.txt"
        ).resolve()

    @property
    def _output_filename(self):
        output_file = self.file_meta.document_id + ".json"
        return Path(self.standard_config.output_dir) / self.config.index_name / output_file

    def cleanup_file(self):
        pass
        """Removes the local copy the file after successful processing."""
        if not self.standard_config.preserve_downloads:
            logger.info(f"Cleaning up document {self.filename}")
            os.unlink(self._tmp_download_file())

    def skip_file(self):
        """Returns a boolean value indicating if download for a file should be skipped"""
        if (
            not self.standard_config.re_download
            and self.filename.is_file()
            and self.filename.stat()
        ):
            return True
        return False

    # TODO: change test fixtures such that examples with
    # nested dictionaries are included in test documents
    def flatten_values(self, value, seperator="\n", no_value_str=""):
        """Flattens list or dict objects. Joins each value or item with
        the seperator character. Keys are not included in the joined string.
        When a dict value or a list item is None, no_value_str is used to
        represent that value / item."""
        if value is None:
            return no_value_str

        if isinstance(value, list):
            flattened_values = [self.flatten_values(item, seperator) for item in value]
            return seperator.join(flattened_values)

        elif isinstance(value, dict):
            flattened_values = [self.flatten_values(item, seperator) for item in value.values()]
            return seperator.join(flattened_values)

        else:
            return str(value)

    def concatenate_dict_fields(self, dictionary, seperator="\n"):
        """Concatenates all values for each key in a dictionary in a nested manner.
        Used to parse a python dictionary to an aggregated string"""
        values = [self.flatten_values(value, seperator) for value in dictionary.values()]
        concatenated_values = seperator.join(values)
        return concatenated_values

    def get_text_fields(self, elasticsearch_query_response):
        """Gets specific fields from the document that is fetched,
        based on the jq query in the config"""
        document = elasticsearch_query_response["hits"]["hits"][0]["_source"]
        if self.config.jq_query:
            document = json.loads(jq.compile(self.config.jq_query).input(document).text())
        return self.concatenate_dict_fields(document)

    @requires_dependencies(["elasticsearch"])
    @BaseIngestDoc.skip_if_file_exists
    def get_file(self):
        if self.skip_file():
            logger.info(f"File exists: {self.filename}, skipping download")
            return

        logger.debug(f"Fetching {self} - PID: {os.getpid()}")

        self.query_to_get_doc_by_id = {
            "bool": {"filter": {"term": {"_id": self.file_meta.document_id}}},
        }

        # TODO: instead of having a separate client for each doc,
        # have a separate client for each process
        es = Elasticsearch(self.config.url)
        response = es.search(index=self.config.index_name, query=self.query_to_get_doc_by_id)

        self.document = self.get_text_fields(response)

        self.filename.parent.mkdir(parents=True, exist_ok=True)
        with open(self.filename, "w", encoding="utf8") as f:
            f.write(self.document)


@requires_dependencies(["elasticsearch"])
@dataclass
class ElasticsearchConnector(ConnectorCleanupMixin, BaseConnector):
    """Fetches particular fields from all documents in a given elasticsearch cluster and index"""

    config: SimpleElasticsearchConfig

    def __init__(
        self,
        standard_config: StandardConnectorConfig,
        config: SimpleElasticsearchConfig,
    ):
        super().__init__(standard_config, config)

    def initialize(self):
        self.es = Elasticsearch(self.config.url)
        self.scan_query: dict = {"query": {"match_all": {}}}
        self.search_query: dict = {"match_all": {}}
        self.es.search(index=self.config.index_name, query=self.search_query, size=1)

    @requires_dependencies(["elasticsearch"])
    def _get_doc_ids(self):
        """Fetches all document ids in an index"""
        hits = scan(
            self.es,
            query=self.scan_query,
            scroll="1m",
            index=self.config.index_name,
        )

        return [hit["_id"] for hit in hits]

    def get_ingest_docs(self):
        """Fetches all documents in an index, using ids that are fetched with _get_doc_ids"""
        ids = self._get_doc_ids()
        return [
            ElasticsearchIngestDoc(
                self.standard_config,
                self.config,
                ElasticsearchFileMeta(self.config.index_name, id),
            )
            for id in ids
        ]
