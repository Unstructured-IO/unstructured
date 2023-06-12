from dataclasses import dataclass

# from typing import Dict, Type
from elasticsearch import Elasticsearch
from elasticsearch.helpers import scan

from unstructured.ingest.interfaces import (
    BaseConnector,
    BaseConnectorConfig,
    BaseIngestDoc,
)

# from unstructured.ingest.logger import logger
from unstructured.utils import requires_dependencies


@dataclass
class SimpleElasticsearchConfig(BaseConnectorConfig):
    cluster_url: str
    index_name: str
    search_query: dict


@dataclass
class ElasticsearchFileMeta:
    index_name: str
    document_id: str


class ElasticsearchIngestDoc(BaseIngestDoc):
    config: SimpleElasticsearchConfig
    file_meta: ElasticsearchFileMeta

    @property
    def filename(self):
        return f"{self.file_meta.index_name}/{self.file_meta.document_id}"

    # TODO
    def cleanup_file(self):
        return super().cleanup_file()

    def get_file(self):
        self.get_doc_by_id_query = {
            "query": {"bool": {"filter": {"term": {"_id": self.file_meta.document_id}}}},
        }
        response = self.es.search(index=self.config.index_name, body=self.get_doc_by_id_query)
        self.json_document = response["hits"]["hits"]

        # TODO: write to disk
        # TODO: checks and logging

    # TODO
    def has_output(self):
        return super().has_output()

    # TODO
    def write_result(self):
        return super().write_result()


class ElasticsearchConnector(BaseConnector):
    config: SimpleElasticsearchConfig

    # TODO
    def cleanup(self, cur_dir=None):
        return super().cleanup(cur_dir)

    @requires_dependencies(["elasticsearch"])
    def initialize(self):
        self.es = Elasticsearch(self.config.cluster_url)
        self.get_all_docs_query = {"query": {"match_all": {}}}
        self.es.search(index=self.config.index_name, body=self.get_all_docs_query, size=1)

    @requires_dependencies(["elasticsearch"])
    def _get_doc_ids(self):
        hits = scan(
            self.es,
            query=self.get_all_docs_query,
            scroll="1m",
            index=self.config.index_name,
        )

        return [hit["_id"] for hit in hits]

    def get_ingest_docs(self, query):
        ids = self._get_doc_ids()
        return [
            ElasticsearchIngestDoc(
                self.standard_config,
                self.config,
                ElasticsearchFileMeta(self.config.index_name, id),
            )
            for id in ids
        ]
