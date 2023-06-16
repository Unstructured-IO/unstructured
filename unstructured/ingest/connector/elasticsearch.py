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
)
from unstructured.ingest.logger import logger
from unstructured.utils import requires_dependencies


@dataclass
class SimpleElasticsearchConfig(BaseConnectorConfig):
    url: str
    index_name: str
    jq_query: Optional[str]


@dataclass
class ElasticsearchFileMeta:
    index_name: str
    document_id: str


@dataclass
class ElasticsearchIngestDoc(BaseIngestDoc):
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

    def _output_filename(self):
        output_file = self.file_meta.document_id + ".json"
        return Path(self.standard_config.output_dir) / self.config.index_name / output_file

    def cleanup_file(self):
        pass
        """Removes the local copy the file after successful processing."""
        if not self.standard_config.preserve_downloads:
            # TODO: forward standard config args and uncomment the if clause
            # if self.config.verbose:
            logger.info(f"Cleaning up document {self.filename}")
            os.unlink(self._tmp_download_file())

    def skip_file(self):
        if (
            not self.standard_config.re_download
            and self.filename.is_file()
            and self.filename.stat()
        ):
            return True
        return False

    def concatenate_dict_fields(self, d):
        result = ""
        for key, value in d.items():
            if value is None:
                continue
            elif isinstance(value, dict):
                result = self.iterate_dict(value, result)
            else:
                result += str(value) + "\n"
        return result

    def get_text_fields(self, elasticsearch_query_response):
        document = elasticsearch_query_response["hits"]["hits"][0]["_source"]
        if self.config.jq_query:
            document = json.loads(jq.compile(self.config.jq_query).input(document).text())
        return self.concatenate_dict_fields(document)

    def get_file(self):
        if self.skip_file():
            logger.debug(f"File exists: {self.filename}, skipping download")
            return

        logger.debug(f"Fetching {self} - PID: {os.getpid()}")

        self.query_to_get_doc_by_id = {
            "query": {"bool": {"filter": {"term": {"_id": self.file_meta.document_id}}}},
        }

        # TODO: instead of having a separate client for each doc,
        # have a separate client for each process
        es = Elasticsearch(self.config.url)
        response = es.search(index=self.config.index_name, body=self.query_to_get_doc_by_id)

        self.document = self.get_text_fields(response)

        self.filename.parent.mkdir(parents=True, exist_ok=True)
        with open(self.filename, "w", encoding="utf8") as f:
            f.write(self.document)

    # TODO
    def has_output(self):
        return super().has_output()

    def write_result(self):
        output_filename = self._output_filename()
        output_filename.parent.mkdir(parents=True, exist_ok=True)
        with open(output_filename, "w") as output_f:
            output_f.write(json.dumps(self.isd_elems_no_filename, ensure_ascii=False, indent=2))
        logger.info(f"Wrote {output_filename}")


@dataclass
class ElasticsearchConnector(BaseConnector):
    config: SimpleElasticsearchConfig

    # TODO: update requires_dependencies decorators

    # TODO
    def cleanup(self, cur_dir=None):
        return super().cleanup(cur_dir)

    @requires_dependencies(["elasticsearch"])
    def initialize(self):
        self.es = Elasticsearch(self.config.url)
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

    def get_ingest_docs(self):
        ids = self._get_doc_ids()
        return [
            ElasticsearchIngestDoc(
                self.standard_config,
                self.config,
                ElasticsearchFileMeta(self.config.index_name, id),
            )
            for id in ids
        ]
