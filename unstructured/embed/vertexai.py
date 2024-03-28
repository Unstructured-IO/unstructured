# type: ignore
import json
import os
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, List, Optional

import numpy as np

from unstructured.documents.elements import (
    Element,
)
from unstructured.embed.interfaces import BaseEmbeddingEncoder, EmbeddingConfig
from unstructured.ingest.error import EmbeddingEncoderConnectionError
from unstructured.utils import FileHandler, requires_dependencies

if TYPE_CHECKING:
    from langchain_google_vertexai import VertexAIEmbeddings


@dataclass
class VertexAIEmbeddingConfig(EmbeddingConfig):
    api_key: str
    model_name: Optional[str] = "textembedding-gecko@001"


@dataclass
class VertexAIEmbeddingEncoder(BaseEmbeddingEncoder):
    config: VertexAIEmbeddingConfig
    _client: Optional["VertexAIEmbeddings"] = field(init=False, default=None)
    _exemplary_embedding: Optional[List[float]] = field(init=False, default=None)

    @property
    def client(self) -> "VertexAIEmbeddings":
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

    def num_of_dimensions(self):
        return np.shape(self.exemplary_embedding)

    def is_unit_vector(self):
        return np.isclose(np.linalg.norm(self.exemplary_embedding), 1.0)

    def embed_query(self, query):
        result = self.client.embed_query(str(query))
        return result

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

    @property
    def application_credentials_path(self):
        return os.path.join("/tmp", "google-vertex-app-credentials.json")

    def register_application_credentials(self):
        credentials_file = FileHandler(self.application_credentials_path)
        credentials_file.write_file(json.dumps(json.loads(self.config.api_key)))
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = self.application_credentials_path

    @EmbeddingEncoderConnectionError.wrap
    @requires_dependencies(
        ["langchain", "langchain_google_vertexai"],
        extras="embed-vertexai",
    )
    def create_client(self) -> "VertexAIEmbeddings":
        """Creates a Langchain VertexAI python client to embed elements."""
        from langchain_google_vertexai import VertexAIEmbeddings

        self.register_application_credentials()
        vertexai_client = VertexAIEmbeddings(model_name=self.config.model_name)
        return vertexai_client
