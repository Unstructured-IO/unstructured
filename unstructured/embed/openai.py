from dataclasses import dataclass, field
from typing import TYPE_CHECKING, List, Optional

import numpy as np

from unstructured.documents.elements import (
    Element,
)
from unstructured.embed.interfaces import BaseEmbeddingEncoder, EmbeddingConfig
from unstructured.ingest.enhanced_dataclass import enhanced_field
from unstructured.ingest.error import EmbeddingEncoderConnectionError
from unstructured.utils import requires_dependencies

if TYPE_CHECKING:
    from langchain_openai.embeddings import OpenAIEmbeddings


@dataclass
class OpenAIEmbeddingConfig(EmbeddingConfig):
    api_key: str = enhanced_field(sensitive=True)
    model_name: str = "text-embedding-ada-002"


@dataclass
class OpenAIEmbeddingEncoder(BaseEmbeddingEncoder):
    config: OpenAIEmbeddingConfig
    _client: Optional["OpenAIEmbeddings"] = field(init=False, default=None)
    _exemplary_embedding: Optional[List[float]] = field(init=False, default=None)

    @property
    def client(self) -> "OpenAIEmbeddings":
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
    @requires_dependencies(["langchain_openai"], extras="openai")
    def create_client(self) -> "OpenAIEmbeddings":
        """Creates a langchain OpenAI python client to embed elements."""
        from langchain_openai import OpenAIEmbeddings

        openai_client = OpenAIEmbeddings(
            openai_api_key=self.config.api_key,
            model=self.config.model_name,  # type:ignore
        )
        return openai_client
