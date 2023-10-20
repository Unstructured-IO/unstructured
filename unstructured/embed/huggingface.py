from typing import List, Optional

import numpy as np

from unstructured.documents.elements import (
    Element,
)
from unstructured.embed.interfaces import BaseEmbeddingEncoder
from unstructured.ingest.error import EmbeddingEncoderConnectionError
from unstructured.utils import requires_dependencies


class HuggingFaceEmbeddingEncoder(BaseEmbeddingEncoder):
    def __init__(
        self,
        model_name: Optional[str] = "sentence-transformers/all-MiniLM-L6-v2",
        model_kwargs: Optional[dict] = {"device": "cpu"},
        encode_kwargs: Optional[dict] = {"normalize_embeddings": False},
        cache_folder: Optional[dict] = None,
    ):
        self.model_name = model_name
        self.model_kwargs = model_kwargs
        self.encode_kwargs = encode_kwargs
        self.cache_folder = cache_folder

        self.initialize()

    def initialize(self):
        """Creates a langchain HuggingFace object to embed elements."""
        self.hf = self.get_huggingface_client()

    def num_of_dimensions(self):
        return np.shape(self.examplary_embedding)

    def is_unit_vector(self):
        return np.isclose(np.linalg.norm(self.examplary_embedding), 1.0)

    def embed_query(self, query):
        return self.hf.embed_query(str(query))

    def embed_documents(self, elements: List[Element]) -> List[Element]:
        embeddings = self.hf.embed_documents([str(e) for e in elements])
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
        ["langchain", "sentence_transformers"],
        extras="embed-huggingface",
    )
    def get_huggingface_client(self):
        """Creates a langchain Huggingface python client to embed elements."""
        if hasattr(self, "hf_client"):
            return self.hf_client

        from langchain.embeddings import HuggingFaceEmbeddings

        hf_client = HuggingFaceEmbeddings(
            model_name=self.model_name,
            model_kwargs=self.model_kwargs,
            encode_kwargs=self.encode_kwargs,
            cache_folder=self.cache_folder,
        )
        self.examplary_embedding = hf_client.embed_query("Q")
        return hf_client
