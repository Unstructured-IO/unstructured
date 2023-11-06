import json
import multiprocessing as mp
import typing as t
from dataclasses import dataclass

from unstructured.ingest.error import DestinationConnectionError, WriteError
from unstructured.ingest.interfaces import (
    BaseConnectorConfig,
    BaseDestinationConnector,
    BaseIngestDoc,
    BaseSessionHandle,
    ConfigSessionHandleMixin,
    WriteConfig,
    WriteConfigSessionHandleMixin,
)
from unstructured.ingest.logger import logger
from unstructured.utils import requires_dependencies
from unstructured.staging.base import flatten_dict


@dataclass
class ChromaSessionHandle(BaseSessionHandle):
    service: "chroma.Index"  # noqa: F821


@dataclass
class ChromaWriteConfig(WriteConfigSessionHandleMixin, ConfigSessionHandleMixin, WriteConfig):
    client: str
    collection_name: str
    # api_key: str
    # index_name: str
    # environment: str
    # todo: fix buggy session handle implementation
    # with the bug, session handle gets created for each batch,
    # rather than with each process

    @requires_dependencies(["chromadb"], extras="chroma")
    def create_chroma_object(self, client, collection_name): #api_key, index_name, environment): # maybe chroma client?
        import chromadb

        chroma_client = chromadb.PersistentClient(path=client)
        collection = chroma_client.get_or_create_collection(name=collection_name)

        # chroma.init(api_key=api_key, environment=environment)
        # index = pinecone.Index(index_name)
        # logger.debug(f"Connected to index: {pinecone.describe_index(index_name)}")
        return collection

    # def create_session_handle(self) -> PineconeSessionHandle:
    #     service = self.create_pinecone_object(self.api_key, self.index_name, self.environment)
    #     return PineconeSessionHandle(service=service)

    @requires_dependencies(["chromadb"], extras="chroma")
    def upsert_batch(self, batch):
        # import pinecone.core.client.exceptions

        # index = self.session_handle.service
        # try:
        #     response = index.upsert(batch)
        # except pinecone.core.client.exceptions.ApiException as api_error:
        #     raise WriteError(f"http error: {api_error}") from api_error
        collection = self.create_chroma_object(self.client, self.collection_name)
        try:
            response = collection.add(batch)
        except Exception as e:
            raise WriteError(f"chroma error: {e}") from e
        logger.debug(f"results: {response}")


@dataclass
class SimpleChromaConfig(BaseConnectorConfig):
    # api_key: str
    # index_name: str
    # environment: str
    client: str
    collection_name: str


@dataclass
class ChromaDestinationConnector(BaseDestinationConnector):
    write_config: WriteConfig
    connector_config: SimpleChromaConfig

    @DestinationConnectionError.wrap
    @requires_dependencies(["chromadb"], extras="chroma")
    def initialize(self):
        pass

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
        # if num_processes == 1:
        for i in range(0, len(dict_list)):
            breakpoint()
            self.write_config.add(ids=dict_list[i]["ids"])  

        # else:
        #     with mp.Pool(
        #         processes=num_processes,
        #     ) as pool:
        #         pool.map(
        #             self.write_config.upsert_batch,
        #             [
        #                 dict_list[i : i + pinecone_batch_size]  # noqa: E203
        #                 for i in range(0, len(dict_list), pinecone_batch_size)
        #             ],  # noqa: E203
        #         )

    def write(self, docs: t.List[BaseIngestDoc]) -> None:
        dict_list: t.List[t.Dict[str, t.Any]] = []
        for doc in docs:
            local_path = doc._output_filename
            with open(local_path) as json_file:
                doc_content = json.load(json_file)
                breakpoint()

                # we want a list of dicts that it can upload one at a time.
                # each dict should have documents (aka text), embeddings, metadatas, and ids

                # documents=["This is a document", "This is another document"],
                # metadatas=[{"source": "my_source"}, {"source": "my_source"}],
                # ids=["id1", "id2"]
                # embeddings=[[1,2,3],[4,5,6]]

                data={}
                #### Add type
                data["ids"]=[x.get("element_id") for x in doc_content]
                data["documents"]=[x.get("text") for x in doc_content]
                data["embeddings"]=[x.get("embeddings") for x in doc_content]
                # flatten this:
                data["metadatas"]=[x.get("metadata") for x in doc_content]


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
                dict_list.append(data)
        self.write_dict(dict_list=dict_list)



