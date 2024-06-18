import copy
import typing as t
import uuid
from dataclasses import dataclass, field
from typing import Any

from unstructured.ingest.enhanced_dataclass import enhanced_field
from unstructured.ingest.enhanced_dataclass.core import _asdict
from unstructured.ingest.error import DestinationConnectionError
from unstructured.ingest.interfaces import (
    AccessConfig,
    BaseConnectorConfig,
    BaseDestinationConnector,
    WriteConfig,
)
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


@dataclass
class CouchbaseWriteConfig(WriteConfig):
    batch_size: int = 50


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
            from datetime import timedelta

            from couchbase.auth import PasswordAuthenticator
            from couchbase.cluster import Cluster
            from couchbase.options import ClusterOptions

            access_conf = self.connector_config.access_config
            connection_string = username = password = None
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
            self._couchbase_cluster = Cluster(connection_string, options)
            self._couchbase_cluster.wait_until_ready(timedelta(seconds=5))
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

        cluster = self.couchbase_cluster
        bucket = cluster.bucket(self.connector_config.bucket)
        scope = bucket.scope(self.connector_config.scope)
        collection = scope.collection(self.connector_config.collection)
        batch_size = self.write_config.batch_size

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
