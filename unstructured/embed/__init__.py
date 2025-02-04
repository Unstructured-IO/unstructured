import warnings

from unstructured.embed.bedrock import BedrockEmbeddingEncoder
from unstructured.embed.huggingface import HuggingFaceEmbeddingEncoder
from unstructured.embed.mixedbreadai import MixedbreadAIEmbeddingEncoder
from unstructured.embed.octoai import OctoAIEmbeddingEncoder
from unstructured.embed.openai import OpenAIEmbeddingEncoder
from unstructured.embed.vertexai import VertexAIEmbeddingEncoder
from unstructured.embed.voyageai import VoyageAIEmbeddingEncoder

EMBEDDING_PROVIDER_TO_CLASS_MAP = {
    "langchain-openai": OpenAIEmbeddingEncoder,
    "langchain-huggingface": HuggingFaceEmbeddingEncoder,
    "langchain-aws-bedrock": BedrockEmbeddingEncoder,
    "langchain-vertexai": VertexAIEmbeddingEncoder,
    "voyageai": VoyageAIEmbeddingEncoder,
    "mixedbread-ai": MixedbreadAIEmbeddingEncoder,
    "octoai": OctoAIEmbeddingEncoder,
}


warnings.warn(
    "unstructured.ingest will be removed in a future version. "
    "Functionality moved to the unstructured-ingest project.",
    DeprecationWarning,
    stacklevel=2,
)
