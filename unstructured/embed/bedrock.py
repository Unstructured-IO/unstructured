from typing import List

import numpy as np

from unstructured.documents.elements import (
    Element,
)
from unstructured.embed.interfaces import BaseEmbeddingEncoder
from unstructured.ingest.error import EmbeddingEncoderConnectionError
from unstructured.utils import requires_dependencies


class BedrockEmbeddingEncoder(BaseEmbeddingEncoder):
    def __init__(
        self,
        aws_access_key_id: str,
        aws_secret_access_key: str,
        region_name: str = "us-west-2",
    ):
        self.aws_access_key_id = aws_access_key_id
        self.aws_secret_access_key = aws_secret_access_key
        self.region_name = region_name
        self.initialize()

    def initialize(self):
        self.bedrock_client = self.get_bedrock_client()

    def num_of_dimensions(self):
        return np.shape(self.examplary_embedding)

    def is_unit_vector(self):
        return np.isclose(np.linalg.norm(self.examplary_embedding), 1.0)

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
        ["boto3", "numpy", "langchain"],
        extras="bedrock",
    )
    def get_bedrock_client(self):
        if getattr(self, "bedrock_client", None):
            return self.bedrock_client

        # delay import only when needed
        import boto3
        from langchain.embeddings import BedrockEmbeddings

        bedrock_runtime = boto3.client(
            service_name="bedrock-runtime",
            aws_access_key_id=self.aws_access_key_id,
            aws_secret_access_key=self.aws_secret_access_key,
            region_name=self.region_name,
        )

        bedrock_client = BedrockEmbeddings(client=bedrock_runtime)
        self.examplary_embedding = np.array(bedrock_client.embed_query("Q"))
        return bedrock_client
