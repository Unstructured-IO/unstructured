import json
from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

from unstructured.ingest.enhanced_dataclass import enhanced_field
from unstructured.ingest.error import DestinationConnectionError
from unstructured.ingest.v2.interfaces import (
    AccessConfig,
    ConnectionConfig,
)
from unstructured.ingest.v2.processes.connector_registry import (
    DestinationRegistryEntry,
    add_destination_entry,
)
from unstructured.ingest.v2.processes.connectors.elasticsearch import (
    ElasticsearchUploader,
    ElasticsearchUploaderConfig,
    ElasticsearchUploadStager,
    ElasticsearchUploadStagerConfig,
)
from unstructured.utils import requires_dependencies

if TYPE_CHECKING:
    from opensearchpy import OpenSearch

CONNECTOR_TYPE = "opensearch"

"""Since the actual OpenSearch project is a fork of Elasticsearch, we are relying
heavily on the Elasticsearch connector code, inheriting the functionality as much as possible."""


@dataclass
class OpenSearchAccessConfig(AccessConfig):
    password: Optional[str] = enhanced_field(default=None, sensitive=True)
    use_ssl: bool = False
    verify_certs: bool = False
    ssl_show_warn: bool = False
    ca_certs: Optional[str] = None
    client_cert: Optional[str] = None
    client_key: Optional[str] = None


@dataclass
class OpenSearchConnectionConfig(ConnectionConfig):
    hosts: Optional[list[str]] = None
    username: Optional[str] = None
    access_config: OpenSearchAccessConfig = enhanced_field(sensitive=True)

    def to_dict(self, **kwargs) -> dict[str, json]:
        d = super().to_dict(**kwargs)
        d.update(self.access_config.to_dict())
        d["http_auth"] = (self.username, self.access_config.password)
        return d

    @DestinationConnectionError.wrap
    @requires_dependencies(["opensearchpy"], extras="opensearch")
    def get_client(self) -> "OpenSearch":
        from opensearchpy import OpenSearch

        return OpenSearch(**self.to_dict(apply_name_overload=False))


@dataclass
class OpenSearchUploader(ElasticsearchUploader):
    connection_config: OpenSearchConnectionConfig

    def load_parallel_bulk(self):
        from opensearchpy.helpers import parallel_bulk

        return parallel_bulk


add_destination_entry(
    destination_type=CONNECTOR_TYPE,
    entry=DestinationRegistryEntry(
        connection_config=OpenSearchConnectionConfig,
        upload_stager_config=ElasticsearchUploadStagerConfig,
        upload_stager=ElasticsearchUploadStager,
        uploader_config=ElasticsearchUploaderConfig,
        uploader=OpenSearchUploader,
    ),
)
