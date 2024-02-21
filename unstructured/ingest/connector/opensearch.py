import typing as t
from dataclasses import dataclass, field

from dataclasses_json.core import Json

from unstructured.ingest.connector.elasticsearch import (
    ElasticsearchDestinationConnector,
    ElasticsearchDocumentMeta,
    ElasticsearchIngestDoc,
    ElasticsearchIngestDocBatch,
    ElasticsearchSourceConnector,
    SimpleElasticsearchConfig,
)
from unstructured.ingest.enhanced_dataclass import enhanced_field
from unstructured.ingest.error import DestinationConnectionError, SourceConnectionError
from unstructured.ingest.interfaces import AccessConfig, BaseSingleIngestDoc
from unstructured.ingest.logger import logger
from unstructured.ingest.utils.data_prep import generator_batching_wbytes
from unstructured.staging.base import flatten_dict
from unstructured.utils import requires_dependencies

if t.TYPE_CHECKING:
    from opensearchpy import OpenSearch

"""Since the actual OpenSearch project is a fork of Elasticsearch, we are relying
heavily on the Elasticsearch connector code, inheriting the functionality as much as possible."""


@dataclass
class OpenSearchAccessConfig(AccessConfig):
    hosts: t.Optional[t.List[str]] = None
    username: t.Optional[str] = None
    password: t.Optional[str] = enhanced_field(default=None, sensitive=True)
    use_ssl: bool = False
    verify_certs: bool = False
    ssl_show_warn: bool = False
    ca_certs: t.Optional[str] = None
    client_cert: t.Optional[str] = None
    client_key: t.Optional[str] = None

    def to_dict(self, **kwargs) -> t.Dict[str, Json]:
        d = super().to_dict(**kwargs)
        d["http_auth"] = (self.username, self.password)
        return d


@dataclass
class SimpleOpenSearchConfig(SimpleElasticsearchConfig):
    access_config: OpenSearchAccessConfig = None


@dataclass
class OpenSearchIngestDoc(ElasticsearchIngestDoc):
    """Class encapsulating fetching a doc and writing processed results (but not
    doing the processing!).

    Current implementation creates a python OpenSearch client to fetch each doc,
    rather than creating a client for each thread.
    """

    connector_config: SimpleOpenSearchConfig
    registry_name: str = "opensearch"

    @SourceConnectionError.wrap
    @requires_dependencies(["opensearchpy"], extras="opensearch")
    @BaseSingleIngestDoc.skip_if_file_exists
    def get_file(self):
        pass


@dataclass
class OpenSearchIngestDocBatch(ElasticsearchIngestDocBatch):
    connector_config: SimpleOpenSearchConfig
    ingest_docs: t.List[OpenSearchIngestDoc] = field(default_factory=list)
    registry_name: str = "opensearch_batch"

    @requires_dependencies(["opensearchpy"], extras="opensearch")
    def _get_docs(self):
        from opensearchpy import OpenSearch
        from opensearchpy.helpers import scan

        ops = OpenSearch(**self.connector_config.access_config.to_dict(apply_name_overload=False))
        scan_query = {
            "_source": self.connector_config.fields,
            "version": True,
            "query": {"ids": {"values": self.list_of_ids}},
        }

        result = scan(
            ops,
            query=scan_query,
            scroll="1m",
            index=self.connector_config.index_name,
        )
        return list(result)

    @SourceConnectionError.wrap
    @requires_dependencies(["opensearchpy"], extras="opensearch")
    def get_files(self):
        documents = self._get_docs()
        for doc in documents:
            ingest_doc = OpenSearchIngestDoc(
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
            str_values = [str(value) for value in flattened_dict.values()]
            concatenated_values = "\n".join(str_values)

            filename.parent.mkdir(parents=True, exist_ok=True)
            with open(filename, "w", encoding="utf8") as f:
                f.write(concatenated_values)
            self.ingest_docs.append(ingest_doc)


@dataclass
class OpenSearchSourceConnector(ElasticsearchSourceConnector):
    """Fetches particular fields from all documents in a given opensearch cluster and index"""

    connector_config: SimpleOpenSearchConfig
    _ops: t.Optional["OpenSearch"] = field(init=False, default=None)

    @property
    def ops(self):
        from opensearchpy import OpenSearch

        if self._ops is None:
            self._ops = OpenSearch(
                **self.connector_config.access_config.to_dict(apply_name_overload=False)
            )
        return self._ops

    def check_connection(self):
        try:
            assert self.ops.ping()
        except Exception as e:
            logger.error(f"failed to validate connection: {e}", exc_info=True)
            raise SourceConnectionError(f"failed to validate connection: {e}")

    @requires_dependencies(["opensearchpy"], extras="opensearch")
    def _get_doc_ids(self):
        """Fetches all document ids in an index"""
        from opensearchpy.helpers import scan

        hits = scan(
            self.ops,
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
            OpenSearchIngestDocBatch(
                connector_config=self.connector_config,
                processor_config=self.processor_config,
                read_config=self.read_config,
                list_of_ids=batched_ids,
            )
            for batched_ids in id_batches
        ]


@dataclass
class OpenSearchDestinationConnector(ElasticsearchDestinationConnector):
    connector_config: SimpleOpenSearchConfig
    _client: t.Optional["OpenSearch"] = field(init=False, default=None)

    @DestinationConnectionError.wrap
    @requires_dependencies(["opensearchpy"], extras="opensearch")
    def generate_client(self) -> "OpenSearch":
        from opensearchpy import OpenSearch

        return OpenSearch(**self.connector_config.access_config.to_dict(apply_name_overload=False))

    @requires_dependencies(["opensearchpy"], extras="opensearch")
    def write_dict(self, *args, elements_dict: t.List[t.Dict[str, t.Any]]) -> None:
        logger.info(
            f"writing document batches to destination"
            f" index named {self.connector_config.index_name}"
            f" at {self.connector_config.access_config.hosts}"
            f" with batch size (in bytes) {self.write_config.batch_size_bytes}"
            f" with {self.write_config.num_processes} (number of) processes"
        )
        from opensearchpy.helpers import parallel_bulk

        for batch in generator_batching_wbytes(
            elements_dict, batch_size_limit_bytes=self.write_config.batch_size_bytes
        ):
            for success, info in parallel_bulk(
                self.client, batch, thread_count=self.write_config.num_processes
            ):
                if not success:
                    logger.error(
                        "upload failed for a batch in opensearch destination connector:", info
                    )
