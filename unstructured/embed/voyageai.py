from dataclasses import dataclass, field
from typing import TYPE_CHECKING, List, Optional

import numpy as np

from unstructured.documents.elements import Element
from unstructured.embed.interfaces import BaseEmbeddingEncoder, EmbeddingConfig
from unstructured.ingest.error import EmbeddingEncoderConnectionError
from unstructured.utils import requires_dependencies

if TYPE_CHECKING:
    from langchain_voyageai import VoyageAIEmbeddings


@dataclass
class VoyageAIEmbeddingConfig(EmbeddingConfig):
    api_key: str
    model_name: str
    batch_size: Optional[int] = None
    truncation: Optional[bool] = None


@dataclass
class VoyageAIEmbeddingEncoder(BaseEmbeddingEncoder):
    config: VoyageAIEmbeddingConfig
    _client: Optional["VoyageAIEmbeddings"] = field(init=False, default=None)
    _exemplary_embedding: Optional[List[float]] = field(init=False, default=None)

    @property
    def client(self) -> "VoyageAIEmbeddings":
        if self._client is None:
            self._client = self.create_client()
        return self._client

    @property
    def exemplary_embedding(self) -> List[float]:
        if self._exemplary_embedding is None:
            self._exemplary_embedding = self.client.embed_query("A sample query.")
        return self._exemplary_embedding

    def initialize(self):
        pass

    @property
    def num_of_dimensions(self) -> tuple[int, ...]:
        return np.shape(self.exemplary_embedding)

    @property
    def is_unit_vector(self) -> bool:
        return np.isclose(np.linalg.norm(self.exemplary_embedding), 1.0)

    def embed_documents(self, elements: List[Element]) -> List[Element]:
        embeddings = self.client.embed_documents([str(e) for e in elements])
        return self._add_embeddings_to_elements(elements, embeddings)

    def embed_query(self, query: str) -> List[float]:
        return self.client.embed_query(query)

    @staticmethod
    def _add_embeddings_to_elements(elements, embeddings) -> List[Element]:
        assert len(elements) == len(embeddings)
        elements_w_embedding = []
        for i, element in enumerate(elements):
            element.embeddings = embeddings[i]
            elements_w_embedding.append(element)
        return elements

    @EmbeddingEncoderConnectionError.wrap
    @requires_dependencies(
        ["langchain", "langchain_voyageai"],
        extras="embed-voyageai",
    )
    def create_client(self) -> "VoyageAIEmbeddings":
        """Creates a Langchain VoyageAI python client to embed elements."""
        from langchain_voyageai import VoyageAIEmbeddings

        return VoyageAIEmbeddings(
            voyage_api_key=self.config.api_key,
            model=self.config.model_name,
            batch_size=self.config.batch_size,
            truncation=self.config.truncation,
        )
