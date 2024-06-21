import hashlib
import json
import sys
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from time import time
from typing import TYPE_CHECKING, Any, Generator, Optional

from unstructured.documents.elements import DataSourceMetadata
from unstructured.ingest.enhanced_dataclass import enhanced_field
from unstructured.ingest.error import SourceConnectionNetworkError
from unstructured.ingest.utils.data_prep import generator_batching_wbytes
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
from unstructured.ingest.v2.logger import logger
from unstructured.ingest.v2.processes.connector_registry import (
    DestinationRegistryEntry,
    SourceRegistryEntry,
    add_destination_entry,
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

    def get_client_kwargs(self) -> dict:
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
        return client_kwargs

    @requires_dependencies(["elasticsearch"], extras="elasticsearch")
    def get_client(self) -> "ElasticsearchClient":
        from elasticsearch import Elasticsearch as ElasticsearchClient

        return ElasticsearchClient(**self.get_client_kwargs())


@dataclass
class ElasticsearchIndexerConfig(IndexerConfig):
    index_name: str
    batch_size: int = 100


@dataclass
class ElasticsearchIndexer(Indexer):
    connection_config: ElasticsearchConnectionConfig
    index_config: ElasticsearchIndexerConfig
    client: "ElasticsearchClient" = field(init=False)
    connector_type: str = CONNECTOR_TYPE

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

    @requires_dependencies(["elasticsearch"], extras="elasticsearch")
    async def run_async(self, file_data: FileData, **kwargs: Any) -> download_responses:
        from elasticsearch import AsyncElasticsearch as AsyncElasticsearchClient
        from elasticsearch.helpers import async_scan

        index_name: str = file_data.additional_metadata["index_name"]
        ids: list[str] = file_data.additional_metadata["ids"]

        scan_query = {
            "_source": self.download_config.fields,
            "version": True,
            "query": {"ids": {"values": ids}},
        }

        download_responses = []
        async with AsyncElasticsearchClient(**self.connection_config.get_client_kwargs()) as client:
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
class ElasticsearchUploadStagerConfig(UploadStagerConfig):
    index_name: str


@dataclass
class ElasticsearchUploadStager(UploadStager):
    upload_stager_config: ElasticsearchUploadStagerConfig

    def conform_dict(self, data: dict) -> dict:
        resp = {
            "_index": self.upload_stager_config.index_name,
            "_id": str(uuid.uuid4()),
            "_source": {
                "element_id": data.pop("element_id", None),
                "embeddings": data.pop("embeddings", None),
                "text": data.pop("text", None),
                "type": data.pop("type", None),
            },
        }
        if "metadata" in data and isinstance(data["metadata"], dict):
            resp["_source"]["metadata"] = flatten_dict(data["metadata"], separator="-")
        return resp

    def run(
        self,
        elements_filepath: Path,
        file_data: FileData,
        output_dir: Path,
        output_filename: str,
        **kwargs: Any,
    ) -> Path:
        with open(elements_filepath) as elements_file:
            elements_contents = json.load(elements_file)
        conformed_elements = [self.conform_dict(data=element) for element in elements_contents]
        output_path = Path(output_dir) / Path(f"{output_filename}.json")
        with open(output_path, "w") as output_file:
            json.dump(conformed_elements, output_file)
        return output_path


@dataclass
class ElasticsearchUploaderConfig(UploaderConfig):
    index_name: str
    batch_size_bytes: int = 15_000_000
    thread_count: int = 4


@dataclass
class ElasticsearchUploader(Uploader):
    upload_config: ElasticsearchUploaderConfig
    connection_config: ElasticsearchConnectionConfig

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
        from elasticsearch.helpers import parallel_bulk

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
                        "upload failed for a batch in elasticsearch destination connector:", info
                    )


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

add_destination_entry(
    destination_type=CONNECTOR_TYPE,
    entry=DestinationRegistryEntry(
        connection_config=ElasticsearchConnectionConfig,
        upload_stager_config=ElasticsearchUploadStagerConfig,
        upload_stager=ElasticsearchUploadStager,
        uploader_config=ElasticsearchUploaderConfig,
        uploader=ElasticsearchUploader,
    ),
)
