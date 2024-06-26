import json
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Optional

from unstructured.ingest.enhanced_dataclass import enhanced_field
from unstructured.ingest.error import (
    DestinationConnectionError,
)
from unstructured.ingest.v2.interfaces import (
    AccessConfig,
    ConnectionConfig,
    FileData,
    download_responses,
)
from unstructured.ingest.v2.processes.connector_registry import (
    DestinationRegistryEntry,
    SourceRegistryEntry,
    add_destination_entry,
    add_source_entry,
)
from unstructured.ingest.v2.processes.connectors.elasticsearch import (
    ElasticsearchDownloader,
    ElasticsearchDownloaderConfig,
    ElasticsearchIndexer,
    ElasticsearchIndexerConfig,
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
class OpenSearchIndexer(ElasticsearchIndexer):
    connection_config: OpenSearchConnectionConfig
    client: "OpenSearch" = field(init=False)

    @requires_dependencies(["opensearchpy"], extras="opensearch")
    def _get_doc_ids(self) -> set[str]:
        """Fetches all document ids in an index"""
        from opensearchpy.helpers import scan

        scan_query: dict = {"stored_fields": [], "query": {"match_all": {}}}
        hits = scan(
            self.client,
            query=scan_query,
            scroll="1m",
            index=self.index_config.index_name,
        )

        return {hit["_id"] for hit in hits}


@dataclass
class OpenSearchDownloader(ElasticsearchDownloader):
    connection_config: OpenSearchConnectionConfig

    @requires_dependencies(["opensearchpy"], extras="opensearch")
    async def run_async(self, file_data: FileData, **kwargs: Any) -> download_responses:
        from opensearchpy import AsyncOpenSearch as AsyncOpenSearchClient
        from opensearchpy.helpers import async_scan

        index_name: str = file_data.additional_metadata["index_name"]
        ids: list[str] = file_data.additional_metadata["ids"]

        scan_query = {
            "_source": self.download_config.fields,
            "version": True,
            "query": {"ids": {"values": ids}},
        }

        download_responses = []
        async with AsyncOpenSearchClient(**self.connection_config.to_dict()) as client:
            async for result in async_scan(
                client,
                query=scan_query,
                scroll="1m",
                index=index_name,
            ):
                download_responses.append(
                    self.generate_download_response(
                        result=result, index_name=index_name, file_data=file_data
                    )
                )
        return download_responses


@dataclass
class OpenSearchUploader(ElasticsearchUploader):
    connection_config: OpenSearchConnectionConfig

    def load_parallel_bulk(self):
        from opensearchpy.helpers import parallel_bulk

        return parallel_bulk


add_source_entry(
    source_type=CONNECTOR_TYPE,
    entry=SourceRegistryEntry(
        connection_config=OpenSearchConnectionConfig,
        indexer=OpenSearchIndexer,
        indexer_config=ElasticsearchIndexerConfig,
        downloader=OpenSearchDownloader,
        downloader_config=ElasticsearchDownloaderConfig,
    ),
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
