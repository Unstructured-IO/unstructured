from typing import List

import numpy as np

from unstructured.documents.elements import (
    Element,
)
from unstructured.embed.interfaces import BaseEmbeddingEncoder
from unstructured.ingest.error import EmbeddingEncoderConnectionError
from unstructured.utils import requires_dependencies


class OpenAIEmbeddingEncoder(BaseEmbeddingEncoder):
    def __init__(self, api_key: str, model_name: str = "text-embedding-ada-002"):
        self.api_key = api_key
        self.model_name = model_name
        self.initialize()

    def initialize(self):
        self.openai_client = self.get_openai_client()

    def num_of_dimensions(self):
        return np.shape(self.examplary_embedding)

    def is_unit_vector(self):
        return np.isclose(np.linalg.norm(self.examplary_embedding), 1.0)

    def embed_query(self, query):
        return self.openai_client.embed_query(str(query))

    def embed_documents(self, elements: List[Element]) -> List[Element]:
        embeddings = self.openai_client.embed_documents([str(e) for e in elements])
        elements_with_embeddings = self._add_embeddings_to_elements(elements, embeddings)
        return elements_with_embeddings

    def _add_embeddings_to_elements(self, elements, embeddings) -> List[Element]:
        assert len(elements) == len(embeddings)
        elements_w_embedding = []
        for i, element in enumerate(elements):
            element.embeddings = embeddings[i]
            elements_w_embedding.append(element)
        return elements

    @EmbeddingEncoderConnectionError.wrap
    @requires_dependencies(
        ["langchain", "openai", "tiktoken"],
        extras="openai",
    )
    def get_openai_client(self):
        if not hasattr(self, "openai_client"):
            """Creates a langchain OpenAI python client to embed elements."""
            from langchain.embeddings.openai import OpenAIEmbeddings

            openai_client = OpenAIEmbeddings(
                openai_api_key=self.api_key,
                model=self.model_name,  # type:ignore
            )

            self.examplary_embedding = openai_client.embed_query("Q")
            return openai_client
