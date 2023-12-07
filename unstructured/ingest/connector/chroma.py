import itertools
import json
import multiprocessing as mp
import typing as t
import uuid
from dataclasses import dataclass

from unstructured.ingest.error import DestinationConnectionError, WriteError
from unstructured.ingest.interfaces import (
    BaseConnectorConfig,
    BaseDestinationConnector,
    BaseIngestDoc,
    ConfigSessionHandleMixin,
    IngestDocSessionHandleMixin,
    WriteConfig,
)
from unstructured.ingest.logger import logger
from unstructured.utils import requires_dependencies
from unstructured.staging.base import flatten_dict

# if t.TYPE_CHECKING:
#     from pinecone import Index as PineconeIndex


@dataclass
class SimpleChromaConfig(ConfigSessionHandleMixin, BaseConnectorConfig):
    # index_name: str
    # environment: str
    # api_key: str = enhanced_field(sensitive=True)
    db_path: str
    collection_name: str


@dataclass
class ChromaWriteConfig(WriteConfig):
    # breakpoint()
    # batch_size: int = 50
    num_processes: int = 1

# @dataclass
# class ChromaSessionHandle(BaseSessionHandle):
#     service: "ChromaIndex"

# @DestinationConnectionError.wrap
# @requires_dependencies(["chromadb"], extras="chroma")
# def create_chroma_object(self, db_path, collection_name): #api_key, index_name, environment): # maybe chroma client?
#     import chromadb

#     chroma_client = chromadb.PersistentClient(path=db_path)
#     print("** getting client **")
#     print(chroma_client)
#     collection = chroma_client.get_or_create_collection(name=collection_name)

#     # chroma.init(api_key=api_key, environment=environment)
#     # index = pinecone.Index(index_name)
#     # logger.debug(f"Connected to index: {pinecone.describe_index(index_name)}")
#     return collection

# @dataclass
# class ChromaWriteConfig(ConfigSessionHandleMixin, WriteConfig):
#     db_path: str # RENAME CLIENT
#     collection_name: str
    # api_key: str
    # index_name: str
    # environment: str
    # todo: fix buggy session handle implementation
    # with the bug, session handle gets created for each batch,
    # rather than with each process


    # def create_session_handle(self) -> ChromaSessionHandle:
    #     service = self.create_chroma_object(self.db_path, self.collection_name)
    #     return ChromaSessionHandle(service=service)

    # @requires_dependencies(["chromadb"], extras="chroma")
    # def upsert_batch(self, batch):

    #     collection = self.session_handle.service
    #     print(collection)

    #     try:
    #         # Chroma wants lists even if there is only one element
    #         response = collection.add(ids=[batch["ids"]], documents=[batch["documents"]], embeddings=[batch["embeddings"]], metadatas=[batch["metadatas"]])
    #     except Exception as e:
    #         raise WriteError(f"chroma error: {e}") from e
    #     logger.debug(f"results: {response}")


@dataclass
class SimpleChromaConfig(BaseConnectorConfig):
    # api_key: str
    # index_name: str
    # environment: str
    db_path: str
    collection_name: str


@dataclass
class ChromaDestinationConnector(BaseDestinationConnector): # IngestDocSessionHandleMixin,
    write_config: ChromaWriteConfig
    connector_config: SimpleChromaConfig
    _collection = None# : t.Optional["PineconeIndex"] = None

    @property
    def chroma_collection(self):
        if self._collection is None:
            self._collection = self.create_collection()
        return self._collection

    def initialize(self):
        pass

    @DestinationConnectionError.wrap
    def check_connection(self):
        create_chroma_object(
            self.db_path, self.collection_name
        )

    @requires_dependencies(["chromadb"], extras="chroma")
    def create_collection(self): #### -> "PineconeIndex":
        import chromadb
        chroma_client = chromadb.PersistentClient(path=self.connector_config.db_path)
        print("** getting client **")
        print(chroma_client)
        # breakpoint()
        collection = chroma_client.get_or_create_collection(name=self.connector_config.collection_name)
        print(collection)
        return collection

    # def create_index(self): #### -> "PineconeIndex":
    #     import chromadb

    #     pinecone.init(
    #         api_key=self.connector_config.api_key, environment=self.connector_config.environment
    #     )
    #     index = pinecone.Index(self.connector_config.index_name)
    #     logger.debug(
    #         f"Connected to index: {pinecone.describe_index(self.connector_config.index_name)}"
    #     )
    #     return index

    @DestinationConnectionError.wrap
    @requires_dependencies(["chromadb"], extras="chroma")
    def upsert_batch(self, batch):

        collection = self.chroma_collection

        try:
            print("%%%%%%%%%%%%% Upserting Batch %%%%%%%%%%%%%%")
            # breakpoint()
            print(batch)
            # Chroma wants lists even if there is only one element
            response = collection.add(ids=batch["ids"], documents=batch["documents"], embeddings=batch["embeddings"], metadatas=batch["metadatas"])
        except Exception as e:
            raise WriteError(f"chroma error: {e}") from e
        logger.debug(f"results: {response}") # Does this do anything?????


    @staticmethod
    def chunks(iterable, batch_size=2):
        """A helper function to break an iterable into chunks of size batch_size."""
        it = iter(iterable)
        chunk = tuple(itertools.islice(it, batch_size))
        while chunk:
            yield chunk
            chunk = tuple(itertools.islice(it, batch_size))

    @staticmethod
    def prepare_chroma_dict(chunk: t.Tuple[t.Dict[str, t.Any]])-> t.Dict[str, t.List[t.Any]]:
        """Helper function to break a tuple of dicts into list of parallel lists for ChromaDb.
        ({'id':1}, {'id':2}, {'id':3}) -> {'ids':[1,2,3]}"""
        # breakpoint()
        chroma_dict = {}
        chroma_dict["ids"] = [x.get("id") for x in chunk]
        chroma_dict["documents"] = [x.get("document") for x in chunk]
        chroma_dict["embeddings"] = [x.get("embedding") for x in chunk]
        chroma_dict["metadatas"] = [x.get("metadata") for x in chunk]
        assert len(chroma_dict["ids"]) == len(chroma_dict["documents"]) == len(chroma_dict["embeddings"]) == len(chroma_dict["metadatas"])
        # print(chroma_dict)
        return chroma_dict

    def write_dict(self, *args, dict_list: t.List[t.Dict[str, t.Any]], **kwargs) -> None:
        logger.info(
            f"Inserting / updating {len(dict_list)} documents to destination "
            # f"index at {self.connector_config.index_name}",
        )

        # this is advised to be 100 at maximum in pinecone docs, however when we
        # chunk content, we hit to the object size limits, so we decrease the batch
        # size even more here

        #THIS IS THE REAL WRITE SPOT. We are not sub batching.
        # pinecone_batch_size = 10

        # num_processes = 1
        # breakpoint()
        if self.write_config.num_processes == 1:
            for chunk in self.chunks(dict_list):# , pinecone_batch_size):
                print(f"len dict list: {len(chunk)}")
                # breakpoint()
                # Here we need to parse out the batch into 4 lists (ids, documents, embeddings, metadatas)
                # and also check that the lengths match.
                
                # upsert_batch expects a dict with 4 lists (ids, documents, embeddings, metadatas)
               
                self.upsert_batch(self.prepare_chroma_dict(chunk))

                # for i in range(0, len(chunk)):
                #     self.upsert_batch(chunk[i])  

        else:
            # breakpoint()
            print("%%%%%%%%%%%%% Multiprocessing %%%%%%%%%%%%%%")
            with mp.Pool(
                processes=self.write_config.num_processes,
            ) as pool:
                # Prepare the list of lists for multiprocessing
                # pool.map expects a list of dicts with 4 lists (ids, documents, embeddings, metadatas)

                # Prepare the list of chunks for multiprocessing
                chunk_list = list(self.chunks(self.prepare_chroma_dict(dict_list)))
                ########## this is nor workiing above ^
                print(f"len chunk list: {len(chunk_list)}")
                print(chunk_list)
                # Upsert each chunk using multiprocessing
                with mp.Pool(processes=self.write_config.num_processes) as pool:
                    pool.map(self.upsert_batch, chunk_list)

    def write(self, docs: t.List[BaseIngestDoc]) -> None:
        dict_list: t.List[t.Dict[str, t.Any]] = []
        for doc in docs:
            local_path = doc._output_filename
            with open(local_path) as json_file:
                dict_content = json.load(json_file)
                # breakpoint()

                # we want a list of dicts that it can upload one at a time.
                # each dict should have documents (aka text), embeddings, metadatas, and ids

                # documents=["This is a document", "This is another document"],
                # metadatas=[{"source": "my_source"}, {"source": "my_source"}],
                # ids=["id1", "id2"]
                # embeddings=[[1,2,3],[4,5,6]]

                # assign element_id and embeddings to "id" and "values"
                # assign everything else to "metadata" field
                dict_content = [
                    {
                        # is element id right id?
                        # "ids": element.pop("element_id", None),
                        "id": str(uuid.uuid4()),
                        "embedding": element.pop("embeddings", None),
                        "document": element.pop("text", None),
                        "metadata": flatten_dict({k: v for k, v in element.items()},separator="-",flatten_lists=True),
                    }
                    for element in dict_content
                ]
                logger.info(
                    f"Extending {len(dict_content)} json elements from content in {local_path}",
                )
                dict_list.extend(dict_content)
                # breakpoint()

                # data={}
                # #### Add type
                # data["ids"]=[x.get("element_id") for x in doc_content]
                # data["documents"]=[x.get("text") for x in doc_content]
                # data["embeddings"]=[x.get("embeddings") for x in doc_content]
                # # flatten this:
                # data["metadatas"]=[flatten_dict(x.get("metadata"),flatten_lists=True) for x in doc_content]


                # assign element_id and embeddings to "id" and "values"
                # assign everything else to "metadata" field
                # dict_content = [
                #     {
                #         "id": element.pop("element_id", None),
                #         "values": element.pop("embeddings", None),
                #         "metadata": {k: json.dumps(v) for k, v in element.items()},
                #     }
                #     for element in dict_content
                # ]
                # logger.info(
                #     f"appending {len(dict_content)} json elements from content in {local_path}",
                # )
                # dict_list.append(data)
        self.write_dict(dict_list=dict_list)



