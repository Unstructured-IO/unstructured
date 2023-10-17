from typing import List, Optional

import numpy as np
from langchain.embeddings import HuggingFaceEmbeddings

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

    @EmbeddingEncoderConnectionError.wrap
    @requires_dependencies(
        ["langchain", "sentence_transformers"],
        extras="huggingface",
    )
    def initialize(self):
        """Creates a langchain HuggingFace object to embed elements."""

        self.hf = HuggingFaceEmbeddings(
            model_name=self.model_name,
            model_kwargs=self.model_kwargs,
            encode_kwargs=self.encode_kwargs,
            cache_folder=self.cache_folder,
        )

        self.examplary_embedding = self.hf.embed_query("Q")

        return self.hf

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
