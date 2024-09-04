from dataclasses import dataclass
from typing import TYPE_CHECKING, List, Optional

import numpy as np
from pydantic import Field

from unstructured.documents.elements import (
    Element,
)
from unstructured.embed.interfaces import BaseEmbeddingEncoder, EmbeddingConfig
from unstructured.utils import requires_dependencies

if TYPE_CHECKING:
    from langchain_huggingface.embeddings import HuggingFaceEmbeddings


class HuggingFaceEmbeddingConfig(EmbeddingConfig):
    model_name: Optional[str] = Field(default="sentence-transformers/all-MiniLM-L6-v2")
    model_kwargs: Optional[dict] = Field(default_factory=lambda: {"device": "cpu"})
    encode_kwargs: Optional[dict] = Field(default_factory=lambda: {"normalize_embeddings": False})
    cache_folder: Optional[dict] = Field(default=None)

    @requires_dependencies(
        ["langchain_huggingface"],
        extras="embed-huggingface",
    )
    def get_client(self) -> "HuggingFaceEmbeddings":
        """Creates a langchain Huggingface python client to embed elements."""
        from langchain_huggingface.embeddings import HuggingFaceEmbeddings

        client = HuggingFaceEmbeddings(**self.dict())
        return client


@dataclass
class HuggingFaceEmbeddingEncoder(BaseEmbeddingEncoder):
    config: HuggingFaceEmbeddingConfig

    def get_exemplary_embedding(self) -> List[float]:
        return self.embed_query(query="Q")

    def num_of_dimensions(self):
        exemplary_embedding = self.get_exemplary_embedding()
        return np.shape(exemplary_embedding)

    def is_unit_vector(self):
        exemplary_embedding = self.get_exemplary_embedding()
        return np.isclose(np.linalg.norm(exemplary_embedding), 1.0)

    def embed_query(self, query):
        client = self.config.get_client()
        return client.embed_query(str(query))

    def embed_documents(self, elements: List[Element]) -> List[Element]:
        client = self.config.get_client()
        embeddings = client.embed_documents([str(e) for e in elements])
        elements_with_embeddings = self._add_embeddings_to_elements(elements, embeddings)
        return elements_with_embeddings

    def _add_embeddings_to_elements(self, elements, embeddings) -> List[Element]:
        assert len(elements) == len(embeddings)
        elements_w_embedding = []

        for i, element in enumerate(elements):
            element.embeddings = embeddings[i]
            elements_w_embedding.append(element)
        return elements
