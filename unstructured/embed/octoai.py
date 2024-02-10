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
    from openai import OpenAI

OCTOAI_BASE_URL = "https://text.octoai.run/v1"


@dataclass
class OctoAiEmbeddingConfig(EmbeddingConfig):
    api_key: str
    model_name: str = "thenlper/gte-large"


@dataclass
class OctoAIEmbeddingEncoder(BaseEmbeddingEncoder):
    config: OctoAiEmbeddingConfig
    # Uses the OpenAI SDK
    _client: Optional["OpenAI"] = field(init=False, default=None)
    _exemplary_embedding: Optional[List[float]] = field(init=False, default=None)

    @property
    def client(self) -> "OpenAI":
        if self._client is None:
            self._client = self.create_client()
        return self._client

    @property
    def exemplary_embedding(self) -> List[float]:
        if self._exemplary_embedding is None:
            self._exemplary_embedding = self.embed_query("Q")
        return self._exemplary_embedding

    def initialize(self):
        pass

    def num_of_dimensions(self):
        return np.shape(self.exemplary_embedding)

    def is_unit_vector(self):
        return np.isclose(np.linalg.norm(self.exemplary_embedding), 1.0)

    def embed_query(self, query):
        response = self.client.embeddings.create(input=str(query), model=self.config.model_name)
        return response.data[0].embedding

    def embed_documents(self, elements: List[Element]) -> List[Element]:
        embeddings = [self.embed_query(e) for e in elements]
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
        ["openai", "tiktoken"],
        extras="embed-openai",
    )
    def create_client(self) -> "OpenAI":
        """Creates an OpenAI python client to embed elements. Uses the OpenAI SDK."""
        from openai import OpenAI

        return OpenAI(api_key=self.config.api_key, base_url=OCTOAI_BASE_URL)
