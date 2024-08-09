import copy
import time
import typing as t
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from unstructured.ingest.enhanced_dataclass import enhanced_field
from unstructured.ingest.enhanced_dataclass.core import _asdict
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
from unstructured.staging.base import flatten_dict
from unstructured.utils import requires_dependencies

if t.TYPE_CHECKING:
    from couchbase.cluster import Cluster


@dataclass
class CouchbaseAccessConfig(AccessConfig):
    connection_string: str = enhanced_field(sensitive=True)
    username: str = enhanced_field(sensitive=True)
    password: str = enhanced_field(sensitive=True)


@dataclass
class SimpleCouchbaseConfig(BaseConnectorConfig):
    access_config: CouchbaseAccessConfig
    bucket: str
    scope: str
    collection: str
    batch_size: int = 50

    from couchbase.cluster import Cluster

    @requires_dependencies(["couchbase"], extras="couchbase")
    def connect_to_couchbase(self) -> Cluster:
        from datetime import timedelta

        from couchbase.auth import PasswordAuthenticator
        from couchbase.cluster import Cluster
        from couchbase.options import ClusterOptions

        connection_string = username = password = None
        access_conf = self.access_config
        try:
            if access_conf.connection_string is not None:
                connection_string = access_conf.connection_string
            if access_conf.username is not None:
                username = access_conf.username
            if access_conf.password is not None:
                password = access_conf.password
        except Exception as e:
            raise f"please provide connection string, username and password : {e}"

        auth = PasswordAuthenticator(username, password)
        options = ClusterOptions(auth)
        options.apply_profile("wan_development")
        cluster = Cluster(connection_string, options)
        cluster.wait_until_ready(timedelta(seconds=5))
        return cluster

    @requires_dependencies(["couchbase"], extras="couchbase")
    def get_collection(self, cluster):
        bucket = cluster.bucket(self.bucket)
        scope = bucket.scope(self.scope)
        collection = scope.collection(self.collection)
        return collection


@dataclass
class CouchbaseWriteConfig(WriteConfig):
    pass


@dataclass
class CouchbaseDestinationConnector(BaseDestinationConnector):
    write_config: CouchbaseWriteConfig
    connector_config: SimpleCouchbaseConfig
    _couchbase_cluster: t.Optional["Cluster"] = field(init=False, default=None)

    def to_dict(self, **kwargs):
        """
        The _couchbase_cluster variable in this dataclass breaks deepcopy due to:
        TypeError: cannot pickle '_thread.lock' object
        When serializing, remove it, meaning client data will need to be reinitialized
        when deserialized
        """
        self_cp = copy.copy(self)
        if hasattr(self_cp, "_client"):
            setattr(self_cp, "_client", None)
        return _asdict(self_cp, **kwargs)

    @property
    @requires_dependencies(["couchbase"], extras="couchbase")
    def couchbase_cluster(self) -> "Cluster":
        if self._couchbase_cluster is None:
            self._couchbase_cluster = self.connector_config.connect_to_couchbase()
        return self._couchbase_cluster

    @requires_dependencies(["couchbase"], extras="couchbase")
    @DestinationConnectionError.wrap
    def initialize(self):
        _ = self.couchbase_cluster

    @requires_dependencies(["couchbase"], extras="couchbase")
    def check_connection(self):
        try:
            _ = self.couchbase_cluster
        except Exception as e:
            raise DestinationConnectionError(f"failed to validate connection: {e}")

    def write_dict(self, *args, elements_dict: list[dict[str, Any]], **kwargs) -> None:
        from couchbase.exceptions import CouchbaseException

        collection = self.connector_config.get_collection(self.couchbase_cluster)
        batch_size = self.connector_config.batch_size

        for i in range(0, len(elements_dict), batch_size):
            batch = elements_dict[i : i + batch_size]
            try:
                collection.upsert_multi(batch[0])
            except CouchbaseException as e:
                raise DestinationConnectionError(f"failed to write to couchbase: {e}")

    def normalize_dict(self, element_dict: dict[str, Any]) -> dict[str, Any]:
        print("dict before normalizing is", element_dict)
        return {
            str(uuid.uuid4()): {
                "embedding": element_dict.pop("embeddings", None),
                "text": element_dict.pop("text", None),
                "metadata": element_dict,
            }
        }


@dataclass
class CouchbaseDocumentMeta:
    collection: str
    document_id: str
    date_created: str


@dataclass
class CouchbaseIngestDoc(IngestDocCleanupMixin, BaseSingleIngestDoc):
    connector_config: SimpleCouchbaseConfig
    document_meta: CouchbaseDocumentMeta
    document: dict = field(default_factory=dict)
    registry_name: str = "couchbase"

    @property
    def filename(self):
        print("filename", self.read_config, self.connector_config.collection, self.document_meta)
        return (
            Path(self.read_config.download_dir)
            / self.connector_config.collection
            / f"{self.document_meta.document_id}.txt"
        ).resolve()

    @property
    def _output_filename(self):
        return (
            Path(self.processor_config.output_dir)
            / self.connector_config.collection
            / f"{self.document_meta.document_id}.json"
        )

    def update_source_metadata(self, **kwargs):
        if self.document is None:
            self.source_metadata = SourceMetadata(
                exists=False,
            )
            return
        self.source_metadata = SourceMetadata(
            exists=True,
        )

    @SourceConnectionError.wrap
    @requires_dependencies(["couchbase"], extras="couchbase")
    @BaseSingleIngestDoc.skip_if_file_exists
    def get_file(self):
        pass

    @property
    def record_locator(self) -> t.Optional[t.Dict[str, t.Any]]:
        return {
            "host": self.connector_config.access_config.connection_string,
            "collection": self.connector_config.collection,
            "document_id": self.document_meta.document_id,
        }


@dataclass
class CouchbaseIngestDocBatch(BaseIngestDocBatch):
    connector_config: SimpleCouchbaseConfig
    ingest_docs: t.List[CouchbaseIngestDoc] = field(default_factory=list)
    list_of_ids: t.List[str] = field(default_factory=list)
    registry_name: str = "couchbase_batch"

    @property
    def unique_id(self) -> str:
        return ",".join(sorted(self.list_of_ids))

    @requires_dependencies(["couchbase"], extras="couchbase")
    def _get_docs(self) -> t.List[dict]:
        """Fetches all documents in a collection."""
        collection = self.connector_config.get_collection(
            self.connector_config.connect_to_couchbase()
        )
        return [collection.get(doc_id).content_as[dict] for doc_id in self.list_of_ids]

    def get_files(self):
        documents = self._get_docs()
        for index, doc in enumerate(documents):
            ingest_doc = CouchbaseIngestDoc(
                processor_config=self.processor_config,
                read_config=self.read_config,
                connector_config=self.connector_config,
                document_meta=CouchbaseDocumentMeta(
                    collection=self.connector_config.collection,
                    document_id=self.list_of_ids[index],
                    date_created=doc.get("date_created"),
                ),
                document=doc,
            )
            ingest_doc.update_source_metadata()
            filename = ingest_doc.filename
            flattened_dict = flatten_dict(dictionary=doc)
            str_values = [str(value) for value in flattened_dict.values()]
            concatenated_values = "\n".join(str_values)

            filename.parent.mkdir(parents=True, exist_ok=True)
            with open(filename, "w", encoding="utf8") as f:
                f.write(concatenated_values)

            self.ingest_docs.append(ingest_doc)


@dataclass
class CouchbaseSourceConnector(SourceConnectorCleanupMixin, BaseSourceConnector):
    connector_config: SimpleCouchbaseConfig
    _couchbase_cluster: t.Optional["Cluster"] = field(init=False, default=None)

    @property
    @requires_dependencies(["couchbase"], extras="couchbase")
    def couchbase_cluster(self) -> "Cluster":
        if self._couchbase_cluster is None:
            self._couchbase_cluster = self.connector_config.connect_to_couchbase()
        return self._couchbase_cluster

    @requires_dependencies(["couchbase"], extras="couchbase")
    @SourceConnectionError.wrap
    def initialize(self):
        _ = self.couchbase_cluster

    @requires_dependencies(["couchbase"], extras="couchbase")
    def check_connection(self):
        try:
            _ = self.couchbase_cluster
        except Exception as e:
            raise SourceConnectionError(f"failed to validate connection: {e}")

    @requires_dependencies(["couchbase"], extras="couchbase")
    def _get_doc_ids(self) -> t.List[str]:
        query = (
            f"SELECT META(d).id "
            f"FROM `{self.connector_config.bucket}`."
            f"`{self.connector_config.scope}`."
            f"`{self.connector_config.collection}` as d"
        )

        max_attempts = 5
        attempts = 0
        while attempts < max_attempts:
            try:
                result = self.couchbase_cluster.query(query)
                document_ids = [row["id"] for row in result]
                return document_ids
            except Exception as e:
                attempts += 1
                time.sleep(3)
                if attempts == max_attempts:
                    raise SourceConnectionError(f"failed to get document ids: {e}")

    @requires_dependencies(["couchbase"], extras="couchbase")
    def get_ingest_docs(self):
        """Fetches all documents in a collection, using ids that are fetched with _get_doc_ids"""
        ids = self._get_doc_ids()
        id_batches = [
            ids[i * self.connector_config.batch_size : (i + 1) * self.connector_config.batch_size]
            for i in range(
                (len(ids) + self.connector_config.batch_size - 1)
                // self.connector_config.batch_size
            )
        ]

        return [
            CouchbaseIngestDocBatch(
                connector_config=self.connector_config,
                processor_config=self.processor_config,
                read_config=self.read_config,
                list_of_ids=batched_ids,
            )
            for batched_ids in id_batches
        ]
