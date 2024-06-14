import json
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional, Dict
import uuid
from unstructured.staging.base import flatten_dict
from unstructured.ingest.utils.data_prep import chunk_generator

from dateutil import parser

from unstructured.ingest.enhanced_dataclass import enhanced_field
from unstructured.ingest.v2.interfaces import (
    AccessConfig,
    ConnectionConfig,
    FileData,
    UploadContent,
    Uploader,
    UploaderConfig,
    UploadStager,
    UploadStagerConfig,
)
from unstructured.ingest.v2.logger import logger
from unstructured.ingest.v2.processes.connector_registry import (
    DestinationRegistryEntry,
    add_destination_entry,
)
from unstructured.utils import requires_dependencies
from unstructured.ingest.error import DestinationConnectionError
if TYPE_CHECKING:
    from chromadb import Collection




import typing as t



CONNECTOR_TYPE = "chroma"


@dataclass
class ChromaAccessConfig(AccessConfig):
    settings: Optional[Dict[str, str]] = None
    headers: Optional[Dict[str, str]] = None


@dataclass
class ChromaConnectionConfig(ConnectionConfig):
    access_config: ChromaAccessConfig = enhanced_field(sensitive=True)
    collection_name: str
    path: Optional[str] = None
    tenant: Optional[str] = "default_tenant"
    database: Optional[str] = "default_database"
    host: Optional[str] = None
    port: Optional[int] = None
    ssl: bool = False
    connector_type: str = CONNECTOR_TYPE


@dataclass
class ChromaUploadStagerConfig(UploadStagerConfig):
    pass


@dataclass
class ChromaUploadStager(UploadStager):
    upload_stager_config: ChromaUploadStagerConfig = field(
        default_factory=lambda: ChromaUploadStagerConfig()
    )

    @staticmethod
    def parse_date_string(date_string: str) -> date:
        try:
            timestamp = float(date_string)
            return datetime.fromtimestamp(timestamp)
        except Exception as e:
            logger.debug(f"date {date_string} string not a timestamp: {e}")
        return parser.parse(date_string)

    @classmethod
    def conform_dict(cls, data: dict) -> None:
        """
        Updates the element dictionary to conform to the Chroma schema
        """

        # Dict as string formatting
        if record_locator := data.get("metadata", {}).get("data_source", {}).get("record_locator"):
            # Explicit casting otherwise fails schema type checking
            data["metadata"]["data_source"]["record_locator"] = str(json.dumps(record_locator))

        # Array of items as string formatting
        if points := data.get("metadata", {}).get("coordinates", {}).get("points"):
            data["metadata"]["coordinates"]["points"] = str(json.dumps(points))

        if links := data.get("metadata", {}).get("links", {}):
            data["metadata"]["links"] = str(json.dumps(links))

        if permissions_data := (
            data.get("metadata", {}).get("data_source", {}).get("permissions_data")
        ):
            data["metadata"]["data_source"]["permissions_data"] = json.dumps(permissions_data)

        # Datetime formatting
        if date_created := data.get("metadata", {}).get("data_source", {}).get("date_created"):
            data["metadata"]["data_source"]["date_created"] = cls.parse_date_string(
                date_created
            ).strftime(
                "%Y-%m-%dT%H:%M:%S.%fZ",
            )

        if date_modified := data.get("metadata", {}).get("data_source", {}).get("date_modified"):
            data["metadata"]["data_source"]["date_modified"] = cls.parse_date_string(
                date_modified
            ).strftime(
                "%Y-%m-%dT%H:%M:%S.%fZ",
            )

        if date_processed := data.get("metadata", {}).get("data_source", {}).get("date_processed"):
            data["metadata"]["data_source"]["date_processed"] = cls.parse_date_string(
                date_processed
            ).strftime(
                "%Y-%m-%dT%H:%M:%S.%fZ",
            )

        if last_modified := data.get("metadata", {}).get("last_modified"):
            data["metadata"]["last_modified"] = cls.parse_date_string(last_modified).strftime(
                "%Y-%m-%dT%H:%M:%S.%fZ",
            )

        # String casting
        if version := data.get("metadata", {}).get("data_source", {}).get("version"):
            data["metadata"]["data_source"]["version"] = str(version)

        if page_number := data.get("metadata", {}).get("page_number"):
            data["metadata"]["page_number"] = str(page_number)

        if regex_metadata := data.get("metadata", {}).get("regex_metadata"):
            data["metadata"]["regex_metadata"] = str(json.dumps(regex_metadata))

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
        for element in elements_contents:
            self.conform_dict(data=element)
        output_path = Path(output_dir) / Path(f"{output_filename}.json")
        with open(output_path, "w") as output_file:
            json.dump(elements_contents, output_file)
        return output_path


@dataclass
class ChromaUploaderConfig(UploaderConfig):
    batch_size: int = 100


@dataclass
class ChromaUploader(Uploader):
    upload_config: ChromaUploaderConfig
    connection_config: ChromaConnectionConfig
    # client: Optional["Client"] = field(init=False)
    _collection: Optional["ChromaCollection"] = None

    def __post_init__(self):
        # from chromadb import Collection

        # auth = self._resolve_auth_method()
        self._collection = self.create_collection()
        # self.client = Client(url=self.connection_nfig.host_url, auth_client_secret=auth)

    


    def is_async(self) -> bool:
        # return True
        return False

    # def _resolve_auth_method(self):
    #     access_configs = self.connection_config.access_config
    #     connection_config = self.connection_config

    #     breakpoint()






    #     if connection_config.anonymous:
    #         return None

    #     if access_configs.access_token:
    #         from weaviate.auth import AuthBearerToken

    #         return AuthBearerToken(
    #             access_token=access_configs.access_token,
    #             refresh_token=connection_config.refresh_token,
    #         )
    #     elif access_configs.api_key:
    #         from weaviate.auth import AuthApiKey

    #         return AuthApiKey(api_key=access_configs.api_key)
    #     elif access_configs.client_secret:
    #         from weaviate.auth import AuthClientCredentials

    #         return AuthClientCredentials(
    #             client_secret=access_configs.client_secret, scope=connection_config.scope
    #         )
    #     elif connection_config.username and access_configs.password:
    #         from weaviate.auth import AuthClientPassword

    #         return AuthClientPassword(
    #             username=connection_config.username,
    #             password=access_configs.password,
    #             scope=connection_config.scope,
    #         )
    #     return None

    # @requires_dependencies(["chromadb"], extras="chroma")
    def create_collection(self) -> "ChromaCollection":
        # access_configs = self.connection_config.access_config
        # connection_config = self.connection_config
        import chromadb

        if self.connection_config.path:
            chroma_client = chromadb.PersistentClient(
                path=self.connection_config.path,
                settings=self.connection_config.settings,
                tenant=self.connection_config.tenant,
                database=self.connection_config.database,
            )

        elif self.connection_config.host and self.connection_config.port:
            chroma_client = chromadb.HttpClient(
                host=self.connection_config.host,
                port=self.connection_config.port,
                ssl=self.connection_config.ssl,
                headers=self.connection_config.access_config.headers,
                settings=self.connection_config.access_config.settings,
                tenant=self.connection_config.tenant,
                database=self.connection_config.database,
            )
        else:
            raise ValueError("Chroma connector requires either path or host and port to be set.")

        collection = chroma_client.get_or_create_collection(
            name=self.connection_config.collection_name
        )
        return collection
    
    @DestinationConnectionError.wrap
    @requires_dependencies(["chromadb"], extras="chroma")
    def upsert_batch(self, batch):
        collection = self._collection

        breakpoint()

        try:
            # Chroma wants lists even if there is only one element
            # Upserting to prevent duplicates
            collection.upsert(
                ids=batch["ids"],
                documents=batch["documents"],
                embeddings=batch["embeddings"],
                metadatas=batch["metadatas"],
            )
        except Exception as e:
            raise ValueError(f"chroma error: {e}") from e
    
    @staticmethod
    def prepare_chroma_list(chunk: t.Tuple[t.Dict[str, t.Any]]) -> t.Dict[str, t.List[t.Any]]:
        """Helper function to break a tuple of dicts into list of parallel lists for ChromaDb.
        ({'id':1}, {'id':2}, {'id':3}) -> {'ids':[1,2,3]}"""
        chroma_dict = {}
        chroma_dict["ids"] = [x.get("id") for x in chunk]
        chroma_dict["documents"] = [x.get("document") for x in chunk]
        chroma_dict["embeddings"] = [x.get("embedding") for x in chunk]
        chroma_dict["metadatas"] = [x.get("metadata") for x in chunk]
        # Make sure all lists are of the same length
        assert (
            len(chroma_dict["ids"])
            == len(chroma_dict["documents"])
            == len(chroma_dict["embeddings"])
            == len(chroma_dict["metadatas"])
        )
        return chroma_dict
    # def run(self, contents: list[UploadContent], **kwargs: Any) -> None:
    #     raise NotImplementedError
    def normalize_dict(self, element_dict: dict) -> dict:
        element_id = element_dict.get("element_id", str(uuid.uuid4()))
        return {
            "id": element_id,
            "embedding": element_dict.pop("embeddings", None),
            "document": element_dict.pop("text", None),
            "metadata": flatten_dict(
                element_dict, separator="-", flatten_lists=True, remove_none=True
            ),
        }
    # async def run_async(self, path: Path, file_data: FileData, **kwargs: Any) -> None:
    # def run(self, path: Path, file_data: FileData, **kwargs: Any) -> None:
    def run(self, contents: list[UploadContent], **kwargs: Any) -> None:
        # for content in contents:

        elements_dict = []
        # lets add normalized dicts
        for content in contents:
            with open(content.path) as elements_file:
                # load a list of elements
                elements = json.load(elements_file)
                # normalize dict for them
                normalized_elements = [self.normalize_dict(x) for x in elements]



                # now append the dicts
                for x in normalized_elements:
                    elements_dict.append(x)

        # with open(path) as elements_file:
        #     elements_dict = json.load(elements_file)



        # this is a list of lists

        """
        so now i need to 
        break apart the list
        conform it
        get it in the right format
        batch it
        upload it

        
        
        
        
        """

    

        logger.info(
            f"writing {len(elements_dict)} objects to destination "
            f"collection {self.connection_config.collection_name} "
            f"at {self.connection_config.host}",
        )

        breakpoint()

        logger.info(f"Inserting / updating {len(elements_dict)} documents to destination ")

        # chroma_batch_size = self.upload_config.batch_size

        for chunk in chunk_generator(elements_dict, self.upload_config.batch_size):
            self.upsert_batch(self.prepare_chroma_list(chunk))

        # self.client.batch.configure(batch_size=self.upload_config.batch_size)
        # with self.client.batch as b:
        #     for e in elements_dict:
        #         vector = e.pop("embeddings", None)
        #         b.add_data_object(
        #             e,
        #             self.connection_config.class_name,
        #             vector=vector,
        #         )


add_destination_entry(
    destination_type=CONNECTOR_TYPE,
    entry=DestinationRegistryEntry(
        connection_config=ChromaConnectionConfig,
        uploader=ChromaUploader,
        uploader_config=ChromaUploaderConfig,
        upload_stager=ChromaUploadStager,
        upload_stager_config=ChromaUploadStagerConfig,
    ),
)
