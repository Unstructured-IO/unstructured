import json
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Optional

from unstructured.ingest.enhanced_dataclass import enhanced_field
from unstructured.ingest.error import DestinationConnectionError
from unstructured.ingest.utils.data_prep import generator_batching_wbytes
from unstructured.ingest.v2.interfaces import (
    AccessConfig,
    ConnectionConfig,
    UploadContent,
    Uploader,
)
from unstructured.ingest.v2.logger import logger
from unstructured.ingest.v2.processes.connector_registry import (
    DestinationRegistryEntry,
    add_destination_entry,
)
from unstructured.ingest.v2.processes.connectors.elasticsearch import (
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
        d.update({k:v for k,v in self.access_config.to_dict().items()})
        d["http_auth"] = (self.username, self.access_config.password)
        return d

    @DestinationConnectionError.wrap
    @requires_dependencies(["opensearchpy"], extras="opensearch")
    def get_client(self) -> "OpenSearch":
        from opensearchpy import OpenSearch

        return OpenSearch(**self.to_dict(apply_name_overload=False))


@dataclass
class OpenSearchUploader(Uploader):
    upload_config: ElasticsearchUploaderConfig
    connection_config: OpenSearchConnectionConfig

    def run(self, contents: list[UploadContent], **kwargs: Any) -> None:
        elements_dict = []
        for content in contents:
            with open(content.path) as elements_file:
                elements = json.load(elements_file)
                elements_dict.extend(elements)
        logger.info(
            f"writing document batches to destination"
            f" index named {self.upload_config.index_name}"
            f" at {self.connection_config.hosts}"
            f" with batch size (in bytes) {self.upload_config.batch_size_bytes}"
            f" with {self.upload_config.thread_count} (number of) threads"
        )
        from opensearchpy.helpers import parallel_bulk

        client = self.connection_config.get_client()

        if not client.indices.exists(index=self.upload_config.index_name):
            logger.warning(
                f"OpenSearch index does not exist: "
                f"{self.upload_config.index_name}. "
                f"This may cause issues when uploading."
            )

        for batch in generator_batching_wbytes(
            elements_dict, batch_size_limit_bytes=self.upload_config.batch_size_bytes
        ):
            for success, info in parallel_bulk(
                self.connection_config.get_client(),
                batch,
                thread_count=self.upload_config.thread_count,
            ):
                if not success:
                    logger.error(
                        "upload failed for a batch in opensearch destination connector:", info
                    )


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
