import hashlib
import sys
from dataclasses import dataclass, field
from pathlib import Path
from time import time
from typing import TYPE_CHECKING, Any, Generator, Optional

from unstructured.documents.elements import DataSourceMetadata
from unstructured.ingest.enhanced_dataclass import enhanced_field
from unstructured.ingest.error import SourceConnectionNetworkError
from unstructured.ingest.v2.interfaces import (
    AccessConfig,
    ConnectionConfig,
    Downloader,
    DownloaderConfig,
    DownloadResponse,
    FileData,
    Indexer,
    IndexerConfig,
    download_responses,
)
from unstructured.ingest.v2.logger import logger
from unstructured.ingest.v2.processes.connector_registry import (
    SourceRegistryEntry,
    add_source_entry,
)
from unstructured.staging.base import flatten_dict
from unstructured.utils import requires_dependencies

if TYPE_CHECKING:
    from elasticsearch import Elasticsearch as ElasticsearchClient

CONNECTOR_TYPE = "elasticsearch"


@dataclass
class ElasticsearchAccessConfig(AccessConfig):
    password: Optional[str] = None
    api_key: Optional[str] = enhanced_field(default=None, overload_name="es_api_key")
    bearer_auth: Optional[str] = None
    ssl_assert_fingerprint: Optional[str] = None


@dataclass
class ElasticsearchConnectionConfig(ConnectionConfig):
    hosts: Optional[list[str]] = None
    username: Optional[str] = None
    cloud_id: Optional[str] = None
    api_key_id: Optional[str] = None
    ca_certs: Optional[str] = None
    access_config: ElasticsearchAccessConfig = enhanced_field(sensitive=True)

    @requires_dependencies(["elasticsearch"], extras="elasticsearch")
    def get_client(self) -> "ElasticsearchClient":
        from elasticsearch import Elasticsearch as ElasticsearchClient

        # Update auth related fields to conform to what the SDK expects based on the
        # supported methods:
        # https://www.elastic.co/guide/en/elasticsearch/client/python-api/current/connecting.html
        client_kwargs = {
            "hosts": self.hosts,
        }
        if self.ca_certs:
            client_kwargs["ca_certs"] = self.ca_certs
        if self.access_config.password and (
            self.cloud_id or self.ca_certs or self.access_config.ssl_assert_fingerprint
        ):
            client_kwargs["basic_auth"] = ("elastic", self.access_config.password)
        elif not self.cloud_id and self.username and self.access_config.password:
            client_kwargs["basic_auth"] = (self.username, self.access_config.password)
        elif self.access_config.api_key and self.api_key_id:
            client_kwargs["api_key"] = (self.api_key_id, self.access_config.api_key)
        return ElasticsearchClient(**client_kwargs)


@dataclass
class ElasticsearchIndexerConfig(IndexerConfig):
    index_name: str
    batch_size: int = 100


@dataclass
class ElasticsearchIndexer(Indexer):
    connection_config: ElasticsearchConnectionConfig
    index_config: ElasticsearchIndexerConfig
    client: "ElasticsearchClient" = field(init=False)

    def __post_init__(self):
        self.client = self.connection_config.get_client()

    @requires_dependencies(["elasticsearch"], extras="elasticsearch")
    def _get_doc_ids(self) -> set[str]:
        """Fetches all document ids in an index"""
        from elasticsearch.helpers import scan

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
class ElasticsearchDownloaderConfig(DownloaderConfig):
    fields: list[str] = field(default_factory=list)


@dataclass
class ElasticsearchDownloader(Downloader):
    connection_config: ElasticsearchConnectionConfig
    download_config: ElasticsearchDownloaderConfig
    client: "ElasticsearchClient" = field(init=False)

    def __post_init__(self):
        self.client = self.connection_config.get_client()

    def get_identifier(self, index_name: str, record_id: str) -> str:
        f = f"{index_name}-{record_id}"
        if self.download_config.fields:
            f = "{}-{}".format(
                f,
                hashlib.sha256(",".join(self.download_config.fields).encode()).hexdigest()[:8],
            )
        return f

    def get_results(self, ids: list[str], index_name: str) -> list[dict]:
        from elasticsearch.helpers import scan

        scan_query = {
            "_source": self.download_config.fields,
            "version": True,
            "query": {"ids": {"values": ids}},
        }

        result = scan(
            self.client,
            query=scan_query,
            scroll="1m",
            index=index_name,
        )
        return list(result)

    def map_es_results(self, es_results: dict) -> str:
        doc_body = es_results["_source"]
        flattened_dict = flatten_dict(dictionary=doc_body)
        str_values = [str(value) for value in flattened_dict.values()]
        concatenated_values = "\n".join(str_values)
        return concatenated_values

    def run(self, file_data: FileData, **kwargs: Any) -> download_responses:
        index_name: str = file_data.additional_metadata["index_name"]
        ids: list[str] = file_data.additional_metadata["ids"]

        es_results = self.get_results(ids=ids, index_name=index_name)
        download_responses = []
        for result in es_results:
            record_id = result["_id"]
            filename_id = self.get_identifier(index_name=index_name, record_id=record_id)
            filename = f"{filename_id}.txt"
            download_path = self.download_config.download_dir / Path(filename)
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
                raise SourceConnectionNetworkError(
                    f"failed to download file {file_data.identifier}"
                )
            download_responses.append(
                DownloadResponse(
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
            )
        return download_responses


add_source_entry(
    source_type=CONNECTOR_TYPE,
    entry=SourceRegistryEntry(
        connection_config=ElasticsearchConnectionConfig,
        indexer=ElasticsearchIndexer,
        indexer_config=ElasticsearchIndexerConfig,
        downloader=ElasticsearchDownloader,
        downloader_config=ElasticsearchDownloaderConfig,
    ),
)
