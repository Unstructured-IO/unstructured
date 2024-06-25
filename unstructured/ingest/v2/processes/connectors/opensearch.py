
import hashlib
import json
import sys
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from time import time
from typing import TYPE_CHECKING, Any, Generator, Optional





from unstructured.documents.elements import DataSourceMetadata
from unstructured.ingest.enhanced_dataclass import EnhancedDataClassJsonMixin, enhanced_field
from unstructured.ingest.error import SourceConnectionError, SourceConnectionNetworkError
from unstructured.ingest.utils.data_prep import generator_batching_wbytes
from unstructured.ingest.v2.logger import logger


from unstructured.ingest.enhanced_dataclass import enhanced_field
from unstructured.ingest.error import DestinationConnectionError
from unstructured.ingest.v2.interfaces import (
    AccessConfig,
    ConnectionConfig,
    Downloader,
    DownloaderConfig,
    DownloadResponse,
    FileData,
    Indexer,
    IndexerConfig,
    UploadContent,
    Uploader,
    UploaderConfig,
    UploadStager,
    UploadStagerConfig,
    download_responses,
)
from unstructured.ingest.v2.processes.connector_registry import (
    DestinationRegistryEntry,
    add_destination_entry,
    SourceRegistryEntry,
    add_source_entry,
)

from unstructured.ingest.v2.processes.connectors.elasticsearch import (
    ElasticsearchUploader,
    ElasticsearchUploaderConfig,
    ElasticsearchUploadStager,
    ElasticsearchUploadStagerConfig,
    ElasticsearchIndexerConfig,
    ElasticsearchDownloaderConfig,
)
from unstructured.utils import requires_dependencies
from unstructured.staging.base import flatten_dict
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
class OpenSearchIndexer(Indexer):
    connection_config: OpenSearchConnectionConfig
    index_config: ElasticsearchIndexerConfig
    client: "OpenSearch" = field(init=False)
    connector_type: str = CONNECTOR_TYPE

    def __post_init__(self):
        self.client = self.connection_config.get_client()

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

    def run(self, **kwargs: Any) -> Generator[FileData, None, None]:
        all_ids = self._get_doc_ids()
        ids = list(all_ids)
        id_batches: list[frozenset[str]] = [
            frozenset(
                ids[
                    i
                    * self.index_config.batch_size : (i + 1)  # noqa
                    * self.index_config.batch_size
                ]
            )
            for i in range(
                (len(ids) + self.index_config.batch_size - 1) // self.index_config.batch_size
            )
        ]
        for batch in id_batches:
            # Make sure the hash is always a positive number to create identified
            identified = str(hash(batch) + sys.maxsize + 1)
            yield FileData(
                identifier=identified,
                connector_type=CONNECTOR_TYPE,
                metadata=DataSourceMetadata(
                    url=f"{self.connection_config.hosts[0]}/{self.index_config.index_name}",
                    date_processed=str(time()),
                ),
                additional_metadata={
                    "ids": list(batch),
                    "index_name": self.index_config.index_name,
                },
            )



@dataclass
class OpenSearchDownloader(Downloader):
    connection_config: OpenSearchConnectionConfig
    download_config: ElasticsearchDownloaderConfig
    connector_type: str = CONNECTOR_TYPE

    def is_async(self) -> bool:
        return True

    def get_identifier(self, index_name: str, record_id: str) -> str:
        f = f"{index_name}-{record_id}"
        if self.download_config.fields:
            f = "{}-{}".format(
                f,
                hashlib.sha256(",".join(self.download_config.fields).encode()).hexdigest()[:8],
            )
        return f

    def map_es_results(self, es_results: dict) -> str:
        doc_body = es_results["_source"]
        flattened_dict = flatten_dict(dictionary=doc_body)
        str_values = [str(value) for value in flattened_dict.values()]
        concatenated_values = "\n".join(str_values)
        return concatenated_values

    def generate_download_response(
        self, result: dict, index_name: str, file_data: FileData
    ) -> DownloadResponse:
        record_id = result["_id"]
        filename_id = self.get_identifier(index_name=index_name, record_id=record_id)
        filename = f"{filename_id}.txt"
        download_path = self.download_dir / Path(filename)
        logger.debug(
            f"Downloading results from index {index_name} and id {record_id} to {download_path}"
        )
        download_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(download_path, "w", encoding="utf8") as f:
                f.write(self.map_es_results(es_results=result))
        except Exception as e:
            logger.error(
                f"failed to download from index {index_name} "
                f"and id {record_id} to {download_path}: {e}",
                exc_info=True,
            )
            raise SourceConnectionNetworkError(f"failed to download file {file_data.identifier}")
        return DownloadResponse(
            file_data=FileData(
                identifier=filename_id,
                connector_type=CONNECTOR_TYPE,
                metadata=DataSourceMetadata(
                    version=str(result["_version"]) if "_version" in result else None,
                    date_processed=str(time()),
                    record_locator={
                        "hosts": self.connection_config.hosts,
                        "index_name": index_name,
                        "document_id": record_id,
                    },
                ),
            ),
            path=download_path,
        )

    def run(self, file_data: FileData, **kwargs: Any) -> download_responses:
        raise NotImplementedError()

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
        # async with AsyncOpenSearchClient(**self.connection_config.get_client_kwargs()) as client:
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
