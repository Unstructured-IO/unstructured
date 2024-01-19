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
    from langchain.embeddings.octoai_embeddings import OctoAIEmbeddings


@dataclass
class OctoAIEmbeddingConfig(EmbeddingConfig):
    token: Optional[str]
    model_name: Optional[str] = "instructor-large"


@dataclass
class OctoAIEmbeddingEncoder(BaseEmbeddingEncoder):
    config: Optional["OctoAIEmbeddingConfig"] = field(init=False, default=None)
    _client: Optional["OctoAIEmbeddings"] = field(init=False, default=None)
    _exemplary_embedding: Optional[List[float]] = field(init=False, default=None)

    @property
    def client(self) -> "OctoAIEmbeddings":
        if self._client is None:
            self._client = self.create_client()
        return self._client

    @property
    def exemplary_embedding(self) -> List[float]:
        if self._exemplary_embedding is None:
            self._exemplary_embedding = self.client.embed_query("Q")
        return self._exemplary_embedding

    def initialize(self):
        pass

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
        ["langchain","octoai"],
    )
    def create_client(self) -> "OctoAIEmbeddings":
        """Creates a langchain OctoAI python client to embed elements."""
        from langchain.embeddings.octoai_embeddings import OctoAIEmbeddings

        embeddings = OctoAIEmbeddings(
        endpoint_url="https://instructor-large-f1kzsig6xes9.octoai.run/predict"
    )
        return embeddings
