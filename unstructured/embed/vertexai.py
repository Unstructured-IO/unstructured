# type: ignore
import json
import os
from dataclasses import dataclass
from typing import TYPE_CHECKING, List, Optional

import numpy as np
from pydantic import Field, SecretStr

from unstructured.documents.elements import (
    Element,
)
from unstructured.embed.interfaces import BaseEmbeddingEncoder, EmbeddingConfig
from unstructured.utils import FileHandler, requires_dependencies

if TYPE_CHECKING:
    from langchain_google_vertexai import VertexAIEmbeddings


class VertexAIEmbeddingConfig(EmbeddingConfig):
    api_key: SecretStr
    model_name: Optional[str] = Field(default="textembedding-gecko@001")

    def register_application_credentials(self):
        application_credentials_path = os.path.join("/tmp", "google-vertex-app-credentials.json")
        credentials_file = FileHandler(application_credentials_path)
        credentials_file.write_file(json.dumps(json.loads(self.api_key.get_secret_value())))
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = application_credentials_path

    @requires_dependencies(
        ["langchain", "langchain_google_vertexai"],
        extras="embed-vertexai",
    )
    def get_client(self) -> "VertexAIEmbeddings":
        """Creates a Langchain VertexAI python client to embed elements."""
        from langchain_google_vertexai import VertexAIEmbeddings

        self.register_application_credentials()
        vertexai_client = VertexAIEmbeddings(model_name=self.model_name)
        return vertexai_client


@dataclass
class VertexAIEmbeddingEncoder(BaseEmbeddingEncoder):
    config: VertexAIEmbeddingConfig

    def get_exemplary_embedding(self) -> List[float]:
        return self.embed_query(query="A sample query.")

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
        result = client.embed_query(str(query))
        return result

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
