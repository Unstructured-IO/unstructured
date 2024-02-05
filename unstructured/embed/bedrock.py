from dataclasses import dataclass
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
    from langchain_community.embeddings import BedrockEmbeddings


@dataclass
class BedrockEmbeddingConfig(EmbeddingConfig):
    aws_access_key_id: str = enhanced_field(sensitive=True)
    aws_secret_access_key: str = enhanced_field(sensitive=True)
    region_name: str = "us-west-2"


@dataclass
class BedrockEmbeddingEncoder(BaseEmbeddingEncoder):
    config: BedrockEmbeddingConfig
    _client: Optional["BedrockEmbeddings"] = enhanced_field(init=False, default=None)
    _exemplary_embedding: Optional[List[float]] = enhanced_field(init=False, default=None)

    @property
    def client(self) -> "BedrockEmbeddings":
        if self._client is None:
            self._client = self.create_client()
        return self._client

    @property
    def exemplary_embedding(self) -> List[float]:
        if self._exemplary_embedding is None:
            self._exemplary_embedding = self.client.embed_query("Q")
        return self._exemplary_embedding

    def __post_init__(self):
        self.initialize()

    def initialize(self):
        self.bedrock_client = self.create_client()

    def num_of_dimensions(self):
        return np.shape(self.exemplary_embedding)

    def is_unit_vector(self):
        return np.isclose(np.linalg.norm(self.exemplary_embedding), 1.0)

    def embed_query(self, query):
        return np.array(self.bedrock_client.embed_query(query))

    def embed_documents(self, elements: List[Element]) -> List[Element]:
        embeddings = self.bedrock_client.embed_documents([str(e) for e in elements])
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
        ["boto3", "numpy", "langchain_community"],
        extras="bedrock",
    )
    def create_client(self) -> "BedrockEmbeddings":
        # delay import only when needed
        import boto3
        from langchain_community.embeddings import BedrockEmbeddings

        bedrock_runtime = boto3.client(service_name="bedrock-runtime", **self.config.to_dict())

        bedrock_client = BedrockEmbeddings(client=bedrock_runtime)
        return bedrock_client
