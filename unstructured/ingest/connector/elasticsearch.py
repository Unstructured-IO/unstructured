import hashlib
import json
import typing as t
import uuid
from dataclasses import dataclass, field
from itertools import chain
from pathlib import Path

from dataclasses_json.core import Json

from unstructured.ingest.enhanced_dataclass import enhanced_field
from unstructured.ingest.error import DestinationConnectionError, SourceConnectionError
from unstructured.ingest.interfaces import (
    AccessConfig,
    BaseConnectorConfig,
    BaseDestinationConnector,
    BaseIngestDocBatch,
    BaseSingleIngestDoc,
    BaseSourceConnector,
    IngestDocCleanupMixin,
    SourceConnectorCleanupMixin,
    SourceMetadata,
    WriteConfig,
)
from unstructured.ingest.logger import logger
from unstructured.ingest.utils.data_prep import generator_batching_wbytes
from unstructured.staging.base import flatten_dict
from unstructured.utils import requires_dependencies

if t.TYPE_CHECKING:
    from elasticsearch import Elasticsearch


@dataclass
class ElasticsearchAccessConfig(AccessConfig):
    hosts: t.Optional[t.List[str]] = None
    username: t.Optional[str] = None
    password: t.Optional[str] = enhanced_field(default=None, sensitive=True)
    cloud_id: t.Optional[str] = None
    api_key: t.Optional[str] = enhanced_field(
        default=None, sensitive=True, overload_name="es_api_key"
    )
    api_key_id: t.Optional[str] = None
    bearer_auth: t.Optional[str] = enhanced_field(default=None, sensitive=True)
    ca_certs: t.Optional[str] = None
    ssl_assert_fingerprint: t.Optional[str] = enhanced_field(default=None, sensitive=True)

    def to_dict(self, **kwargs) -> t.Dict[str, Json]:
        d = super().to_dict(**kwargs)
        # Update auth related fields to conform to what the SDK expects based on the
        # supported methods:
        # https://www.elastic.co/guide/en/elasticsearch/client/python-api/current/connecting.html
        if not self.ca_certs:
            # ES library already sets a default for this, don't want to
            # introduce data by setting it to None
            d.pop("ca_certs")
        if self.password and (self.cloud_id or self.ca_certs or self.ssl_assert_fingerprint):
            d.pop("password")
            d["basic_auth"] = ("elastic", self.password)
        elif not self.cloud_id and self.username and self.password:
            d.pop("username", None)
            d.pop("password", None)
            d["basic_auth"] = (self.username, self.password)
        elif self.api_key and self.api_key_id:
            d.pop("api_key_id", None)
            d.pop("api_key", None)
            d["api_key"] = (self.api_key_id, self.api_key)
        # This doesn't exist on the client init, remove:
        d.pop("api_key_id", None)
        return d


@dataclass
class SimpleElasticsearchConfig(BaseConnectorConfig):
    """Connector config where:
    url is the url to access the elasticsearch server,
    index_name is the name of the index to reach to,
    """

    index_name: str
    batch_size: int = 100
    fields: t.List[str] = field(default_factory=list)
    access_config: ElasticsearchAccessConfig = None


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
            "hosts": self.connector_config.access_config.hosts,
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

        es = Elasticsearch(**self.connector_config.access_config.to_dict(apply_name_overload=False))
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
            str_values = [str(value) for value in flattened_dict.values()]
            concatenated_values = "\n".join(str_values)

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
            self._es = Elasticsearch(
                **self.connector_config.access_config.to_dict(apply_name_overload=False)
            )
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


@dataclass
class ElasticsearchWriteConfig(WriteConfig):
    batch_size_bytes: int
    num_processes: int


@dataclass
class ElasticsearchDestinationConnector(BaseDestinationConnector):
    write_config: ElasticsearchWriteConfig
    connector_config: SimpleElasticsearchConfig
    _client: t.Optional["Elasticsearch"] = field(init=False, default=None)

    @DestinationConnectionError.wrap
    @requires_dependencies(["elasticsearch"], extras="elasticsearch")
    def generate_client(self) -> "Elasticsearch":
        from elasticsearch import Elasticsearch

        return Elasticsearch(
            **self.connector_config.access_config.to_dict(apply_name_overload=False)
        )

    @property
    def client(self):
        if self._client is None:
            self._client = self.generate_client()
        return self._client

    def initialize(self):
        _ = self.client

    @DestinationConnectionError.wrap
    def check_connection(self):
        try:
            assert self.client.ping()
        except Exception as e:
            logger.error(f"failed to validate connection: {e}", exc_info=True)
            raise DestinationConnectionError(f"failed to validate connection: {e}")

    @requires_dependencies(["elasticsearch"], extras="elasticsearch")
    def write_dict(self, element_dicts: t.List[t.Dict[str, t.Any]]) -> None:
        logger.info(
            f"writing document batches to destination"
            f" index named {self.connector_config.index_name}"
            f" at {self.connector_config.access_config.hosts}"
            f" with batch size (in bytes) {self.write_config.batch_size_bytes}"
            f" with {self.write_config.num_processes} (number of) processes"
        )
        from elasticsearch.helpers import parallel_bulk

        for batch in generator_batching_wbytes(
            element_dicts, batch_size_limit_bytes=self.write_config.batch_size_bytes
        ):
            for success, info in parallel_bulk(
                self.client, batch, thread_count=self.write_config.num_processes
            ):
                if not success:
                    logger.error(
                        "upload failed for a batch in elasticsearch destination connector:", info
                    )

    def conform_dict(self, element_dict):
        return {
            "_index": self.connector_config.index_name,
            "_id": str(uuid.uuid4()),
            "_source": {
                "element_id": element_dict.pop("element_id", None),
                "embeddings": element_dict.pop("embeddings", None),
                "text": element_dict.pop("text", None),
                "metadata": flatten_dict(
                    element_dict.pop("metadata", None),
                    separator="-",
                ),
            },
        }

    def write(self, docs: t.List[BaseSingleIngestDoc]) -> None:
        def generate_element_dicts(doc):
            with open(doc._output_filename) as json_file:
                element_dicts_one_doc = (
                    self.conform_dict(element_dict) for element_dict in json.load(json_file)
                )
                yield from element_dicts_one_doc

        # We chain to unite the generators into one generator
        self.write_dict(chain(*(generate_element_dicts(doc) for doc in docs)))
