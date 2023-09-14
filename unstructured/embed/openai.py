from typing import List, Optional

from unstructured.documents.elements import (
    Element,
)
from unstructured.embed.interfaces import BaseEmbeddingEncoder
from unstructured.ingest.error import EmbeddingEncoderConnectionError
from unstructured.utils import requires_dependencies


class OpenAIEmbeddingEncoder(BaseEmbeddingEncoder):
    def __init__(self, api_key: str, model_name: Optional[str] = "text-embedding-ada-002"):
        self.api_key = api_key
        self.model_name = model_name
        self.initialize()

    def initialize(self):
        self.openai_client = self.get_openai_client()

    def embed(self, elements: Optional[List[Element]]) -> List[Element]:
        embeddings = self.openai_client.embed_documents([str(e) for e in elements])
        elements_with_embeddings = self._add_embeddings_to_elements(elements, embeddings)
        return elements_with_embeddings

    def _add_embeddings_to_elements(self, elements, embeddings) -> List[Element]:
        assert len(elements) == len(embeddings)
        for i in range(len(elements)):
            elements[i].embeddings = embeddings[i]
        return elements

    @EmbeddingEncoderConnectionError.wrap
    @requires_dependencies(
        ["langchain", "openai"],
    )  # add extras="langchain" when it's added to the makefile
    def get_openai_client(self):
        if not hasattr(self, "openai_client"):
            """Creates a langchain OpenAI python client to embed elements."""
            from langchain.embeddings.openai import OpenAIEmbeddings

            openai_client = OpenAIEmbeddings(
                openai_api_key=self.api_key,
                model=self.model_name,
            )

            _ = openai_client.embed_query("We are testing authentication")
            return openai_client
