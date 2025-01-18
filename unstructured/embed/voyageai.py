from dataclasses import dataclass
from typing import TYPE_CHECKING, List, Optional

import numpy as np
from pydantic import Field, SecretStr

from unstructured.documents.elements import Element
from unstructured.embed.interfaces import BaseEmbeddingEncoder, EmbeddingConfig
from unstructured.utils import requires_dependencies

if TYPE_CHECKING:
    from voyageai import Client


class VoyageAIEmbeddingConfig(EmbeddingConfig):
    api_key: SecretStr
    model_name: str
    batch_size: Optional[int] = Field(default=None)
    truncation: Optional[bool] = Field(default=None)
    output_dimension: Optional[int] = Field(default=None)

    @requires_dependencies(
        ["voyageai"],
        extras="embed-voyageai",
    )
    def get_client(self) -> "Client":
        """Creates a VoyageAI python client to embed elements."""
        from voyageai import Client

        return Client(
            api_key=self.api_key.get_secret_value(),
        )


@dataclass
class VoyageAIEmbeddingEncoder(BaseEmbeddingEncoder):
    config: VoyageAIEmbeddingConfig

    def get_exemplary_embedding(self) -> List[float]:
        return self.embed_query(query="A sample query.")

    def initialize(self):
        pass

    @property
    def num_of_dimensions(self) -> tuple[int, ...]:
        exemplary_embedding = self.get_exemplary_embedding()
        return np.shape(exemplary_embedding)

    @property
    def is_unit_vector(self) -> bool:
        exemplary_embedding = self.get_exemplary_embedding()
        return np.isclose(np.linalg.norm(exemplary_embedding), 1.0)

    def embed_documents(self, elements: List[Element]) -> List[Element]:
        client = self.config.get_client()
        embeddings = client.embed(
            texts=[str(e) for e in elements],
            model=self.config.model_name,
            input_type="document",
            truncation=self.config.truncation,
            output_dimension=self.config.output_dimension,
        ).embeddings
        return self._add_embeddings_to_elements(elements, embeddings)

    def embed_query(self, query: str) -> List[float]:
        client = self.config.get_client()
        return client.embed(
            texts=[query],
            model=self.config.model_name,
            input_type="query",
            truncation=self.config.truncation,
            output_dimension=self.config.output_dimension,
        ).embeddings[0]

    @staticmethod
    def _add_embeddings_to_elements(elements, embeddings) -> List[Element]:
        assert len(elements) == len(embeddings)
        elements_w_embedding = []
        for i, element in enumerate(elements):
            element.embeddings = embeddings[i]
            elements_w_embedding.append(element)
        return elements
