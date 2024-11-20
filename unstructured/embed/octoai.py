from dataclasses import dataclass, field
from typing import TYPE_CHECKING, List, Optional

import numpy as np
from pydantic import Field, SecretStr

from unstructured.documents.elements import (
    Element,
)
from unstructured.embed.interfaces import BaseEmbeddingEncoder, EmbeddingConfig
from unstructured.utils import requires_dependencies

if TYPE_CHECKING:
    from openai import OpenAI


class OctoAiEmbeddingConfig(EmbeddingConfig):
    api_key: SecretStr
    model_name: str = Field(default="thenlper/gte-large")
    base_url: str = Field(default="https://text.octoai.run/v1")

    @requires_dependencies(
        ["openai", "tiktoken"],
        extras="embed-octoai",
    )
    def get_client(self) -> "OpenAI":
        """Creates an OpenAI python client to embed elements. Uses the OpenAI SDK."""
        from openai import OpenAI

        return OpenAI(api_key=self.api_key.get_secret_value(), base_url=self.base_url)


@dataclass
class OctoAIEmbeddingEncoder(BaseEmbeddingEncoder):
    config: OctoAiEmbeddingConfig
    # Uses the OpenAI SDK
    _exemplary_embedding: Optional[List[float]] = field(init=False, default=None)

    def get_exemplary_embedding(self) -> List[float]:
        return self.embed_query("Q")

    def initialize(self):
        pass

    def num_of_dimensions(self):
        exemplary_embedding = self.get_exemplary_embedding()
        return np.shape(exemplary_embedding)

    def is_unit_vector(self):
        exemplary_embedding = self.get_exemplary_embedding()
        return np.isclose(np.linalg.norm(exemplary_embedding), 1.0)

    def embed_query(self, query):
        client = self.config.get_client()
        response = client.embeddings.create(input=str(query), model=self.config.model_name)
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
