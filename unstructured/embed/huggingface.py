from dataclasses import dataclass, field
from typing import TYPE_CHECKING, List, Optional

import numpy as np

from unstructured.documents.elements import (
    Element,
)
from unstructured.embed.interfaces import BaseEmbeddingEncoder, EmbeddingConfig
from unstructured.ingest.error import EmbeddingEncoderConnectionError
from unstructured.utils import requires_dependencies

if TYPE_CHECKING:
    from langchain_community.embeddings import HuggingFaceEmbeddings


@dataclass
class HuggingFaceEmbeddingConfig(EmbeddingConfig):
    model_name: Optional[str] = "sentence-transformers/all-MiniLM-L6-v2"
    model_kwargs: Optional[dict] = field(default_factory=lambda: {"device": "cpu"})
    encode_kwargs: Optional[dict] = field(default_factory=lambda: {"normalize_embeddings": False})
    cache_folder: Optional[dict] = None


@dataclass
class HuggingFaceEmbeddingEncoder(BaseEmbeddingEncoder):
    config: HuggingFaceEmbeddingConfig
    _client: Optional["HuggingFaceEmbeddings"] = field(init=False, default=None)
    _exemplary_embedding: Optional[List[float]] = field(init=False, default=None)

    @property
    def client(self) -> "HuggingFaceEmbeddings":
        if self._client is None:
            self._client = self.create_client()
        return self._client

    @property
    def exemplary_embedding(self) -> List[float]:
        if self._exemplary_embedding is None:
            self._exemplary_embedding = self.client.embed_query("Q")
        return self._exemplary_embedding

    def initialize(self):
        """Creates a langchain HuggingFace object to embed elements."""
        _ = self.client

    def num_of_dimensions(self):
        return np.shape(self.exemplary_embedding)

    def is_unit_vector(self):
        return np.isclose(np.linalg.norm(self.exemplary_embedding), 1.0)

    def embed_query(self, query):
        return self.client.embed_query(str(query))

    def embed_documents(self, elements: List[Element]) -> List[Element]:
        embeddings = self.client.embed_documents([str(e) for e in elements])
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
        ["langchain_community", "sentence_transformers"],
        extras="embed-huggingface",
    )
    def create_client(self) -> "HuggingFaceEmbeddings":
        """Creates a langchain Huggingface python client to embed elements."""
        from langchain_community.embeddings import HuggingFaceEmbeddings

        client = HuggingFaceEmbeddings(**self.config.to_dict())
        return client
