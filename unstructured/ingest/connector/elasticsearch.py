import hashlib
import os
import typing as t
from dataclasses import dataclass, field
from pathlib import Path

from unstructured.ingest.error import SourceConnectionError
from unstructured.ingest.interfaces import (
    BaseConnectorConfig,
    BaseIngestDocBatch,
    BaseSingleIngestDoc,
    BaseSourceConnector,
    IngestDocCleanupMixin,
    SourceConnectorCleanupMixin,
    SourceMetadata,
)
from unstructured.ingest.logger import logger
from unstructured.staging.base import flatten_dict
from unstructured.utils import requires_dependencies

if t.TYPE_CHECKING:
    from elasticsearch import Elasticsearch


@dataclass
class SimpleElasticsearchConfig(BaseConnectorConfig):
    """Connector config where:
    url is the url to access the elasticsearch server,
    index_name is the name of the index to reach to,
    """

    url: str
    index_name: str
    batch_size: int = 100
    fields: t.List[str] = field(default=list)


@dataclass
class ElasticsearchDocumentMeta:
    """Metadata specifying:
    name of the elasticsearch index that is being reached to,
    and the id of document that is being reached to,
    """

    index_name: str
    document_id: str


@dataclass
class ElasticsearchIngestDoc(IngestDocCleanupMixin, BaseSingleIngestDoc):
    """Class encapsulating fetching a doc and writing processed results (but not
    doing the processing!).

    Current implementation creates a python Elasticsearch client to fetch each doc,
    rather than creating a client for each thread.
    """

    connector_config: SimpleElasticsearchConfig
    document_meta: ElasticsearchDocumentMeta
    document: dict = field(default_factory=dict)
    registry_name: str = "elasticsearch"

    # TODO: remove one of filename or _tmp_download_file, using a wrapper
    @property
    def filename(self):
        f = self.document_meta.document_id
        if self.connector_config.fields:
            f = "{}-{}".format(
                f,
                hashlib.sha256(",".join(self.connector_config.fields).encode()).hexdigest()[:8],
            )
        return (
            Path(self.read_config.download_dir) / self.document_meta.index_name / f"{f}.txt"
        ).resolve()

    @property
    def _output_filename(self):
        """Create filename document id combined with a hash of the query to uniquely identify
        the output file."""
        # Generate SHA256 hash and take the first 8 characters
        filename = self.document_meta.document_id
        if self.connector_config.fields:
            filename = "{}-{}".format(
                filename,
                hashlib.sha256(",".join(self.connector_config.fields).encode()).hexdigest()[:8],
            )
        output_file = f"{filename}.json"
        return (
            Path(self.processor_config.output_dir) / self.connector_config.index_name / output_file
        )

    def update_source_metadata(self, **kwargs):
        if self.document is None:
            self.source_metadata = SourceMetadata(
                exists=False,
            )
            return
        self.source_metadata = SourceMetadata(
            version=self.document["_version"],
            exists=True,
        )

    @SourceConnectionError.wrap
    @requires_dependencies(["elasticsearch"], extras="elasticsearch")
    @BaseSingleIngestDoc.skip_if_file_exists
    def get_file(self):
        pass

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
class ElasticsearchIngestDocBatch(BaseIngestDocBatch):
    connector_config: SimpleElasticsearchConfig
    ingest_docs: t.List[ElasticsearchIngestDoc] = field(default_factory=list)
    list_of_ids: t.List[str] = field(default_factory=list)
    registry_name: str = "elasticsearch_batch"

    def __post_init__(self):
        # Until python3.8 is deprecated, this is a limitation of dataclass inheritance
        # to make it a required field
        if len(self.list_of_ids) == 0:
            raise ValueError("list_of_ids is required")

    @property
    def unique_id(self) -> str:
        return ",".join(sorted(self.list_of_ids))

    @requires_dependencies(["elasticsearch"], extras="elasticsearch")
    def _get_docs(self):
        from elasticsearch import Elasticsearch
        from elasticsearch.helpers import scan

        es = Elasticsearch(self.connector_config.url)
        scan_query = {
            "_source": self.connector_config.fields,
            "version": True,
            "query": {"ids": {"values": self.list_of_ids}},
        }

        result = scan(
            es,
            query=scan_query,
            scroll="1m",
            index=self.connector_config.index_name,
        )
        return list(result)

    @SourceConnectionError.wrap
    @requires_dependencies(["elasticsearch"], extras="elasticsearch")
    def get_files(self):
        logger.debug(f"Fetching {self} - PID: {os.getpid()}")
        documents = self._get_docs()
        for doc in documents:
            ingest_doc = ElasticsearchIngestDoc(
                processor_config=self.processor_config,
                read_config=self.read_config,
                connector_config=self.connector_config,
                document=doc,
                document_meta=ElasticsearchDocumentMeta(
                    self.connector_config.index_name, doc["_id"]
                ),
            )
            ingest_doc.update_source_metadata()
            doc_body = doc["_source"]
            filename = ingest_doc.filename
            flattened_dict = flatten_dict(dictionary=doc_body)
            concatenated_values = "\n".join(flattened_dict.values())

            filename.parent.mkdir(parents=True, exist_ok=True)
            with open(filename, "w", encoding="utf8") as f:
                f.write(concatenated_values)
            self.ingest_docs.append(ingest_doc)


@dataclass
class ElasticsearchSourceConnector(SourceConnectorCleanupMixin, BaseSourceConnector):
    """Fetches particular fields from all documents in a given elasticsearch cluster and index"""

    connector_config: SimpleElasticsearchConfig
    _es: t.Optional["Elasticsearch"] = field(init=False, default=None)

    @property
    def es(self):
        from elasticsearch import Elasticsearch

        if self._es is None:
            self._es = Elasticsearch(self.connector_config.url)
        return self._es

    def check_connection(self):
        try:
            self.es.perform_request("HEAD", "/", headers={"accept": "application/json"})
        except Exception as e:
            logger.error(f"failed to validate connection: {e}", exc_info=True)
            raise SourceConnectionError(f"failed to validate connection: {e}")

    def __post_init__(self):
        self.scan_query: dict = {"stored_fields": [], "query": {"match_all": {}}}

    def initialize(self):
        pass

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
        id_batches = [
            ids[
                i
                * self.connector_config.batch_size : (i + 1)  # noqa
                * self.connector_config.batch_size
            ]
            for i in range(
                (len(ids) + self.connector_config.batch_size - 1)
                // self.connector_config.batch_size
            )
        ]
        return [
            ElasticsearchIngestDocBatch(
                connector_config=self.connector_config,
                processor_config=self.processor_config,
                read_config=self.read_config,
                list_of_ids=batched_ids,
            )
            for batched_ids in id_batches
        ]
