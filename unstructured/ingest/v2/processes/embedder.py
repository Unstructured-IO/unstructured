from abc import ABC
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from unstructured.documents.elements import Element
from unstructured.embed.interfaces import BaseEmbeddingEncoder
from unstructured.ingest.enhanced_dataclass import EnhancedDataClassJsonMixin, enhanced_field
from unstructured.ingest.v2.interfaces.process import BaseProcess
from unstructured.staging.base import elements_from_json


@dataclass
class EmbedderConfig(EnhancedDataClassJsonMixin):
    embedding_provider: Optional[str] = None
    embedding_api_key: Optional[str] = enhanced_field(default=None, sensitive=True)
    embedding_model_name: Optional[str] = None
    embedding_aws_access_key_id: Optional[str] = None
    embedding_aws_secret_access_key: Optional[str] = None
    embedding_aws_region: Optional[str] = None

    def get_embedder(self) -> BaseEmbeddingEncoder:
        kwargs: dict[str, Any] = {}
        if self.embedding_api_key:
            kwargs["api_key"] = self.embedding_api_key
        if self.embedding_model_name:
            kwargs["model_name"] = self.embedding_model_name
        # TODO make this more dynamic to map to encoder configs
        if self.embedding_provider == "langchain-openai":
            from unstructured.embed.openai import OpenAIEmbeddingConfig, OpenAIEmbeddingEncoder

            return OpenAIEmbeddingEncoder(config=OpenAIEmbeddingConfig(**kwargs))
        elif self.embedding_provider == "langchain-huggingface":
            from unstructured.embed.huggingface import (
                HuggingFaceEmbeddingConfig,
                HuggingFaceEmbeddingEncoder,
            )

            return HuggingFaceEmbeddingEncoder(config=HuggingFaceEmbeddingConfig(**kwargs))
        elif self.embedding_provider == "octoai":
            from unstructured.embed.octoai import OctoAiEmbeddingConfig, OctoAIEmbeddingEncoder

            return OctoAIEmbeddingEncoder(config=OctoAiEmbeddingConfig(**kwargs))
        elif self.embedding_provider == "langchain-aws-bedrock":
            from unstructured.embed.bedrock import BedrockEmbeddingConfig, BedrockEmbeddingEncoder

            return BedrockEmbeddingEncoder(
                config=BedrockEmbeddingConfig(
                    aws_access_key_id=self.embedding_aws_access_key_id,
                    aws_secret_access_key=self.embedding_aws_secret_access_key,
                    region_name=self.embedding_aws_region,
                )
            )
        elif self.embedding_provider == "langchain-vertexai":
            from unstructured.embed.vertexai import (
                VertexAIEmbeddingConfig,
                VertexAIEmbeddingEncoder,
            )

            return VertexAIEmbeddingEncoder(config=VertexAIEmbeddingConfig(**kwargs))
        else:
            raise ValueError(f"{self.embedding_provider} not a recognized encoder")


@dataclass
class Embedder(BaseProcess, ABC):
    config: EmbedderConfig

    def run(self, elements_filepath: Path, **kwargs: Any) -> list[Element]:
        # TODO update base embedder classes to support async
        embedder = self.config.get_embedder()
        elements = elements_from_json(filename=str(elements_filepath))
        if not elements:
            return elements
        return embedder.embed_documents(elements=elements)
