import warnings

from meridian_partition.embed.bedrock import BedrockEmbeddingEncoder
from meridian_partition.embed.huggingface import HuggingFaceEmbeddingEncoder
from meridian_partition.embed.mixedbreadai import MixedbreadAIEmbeddingEncoder
from meridian_partition.embed.octoai import OctoAIEmbeddingEncoder
from meridian_partition.embed.openai import OpenAIEmbeddingEncoder
from meridian_partition.embed.vertexai import VertexAIEmbeddingEncoder
from meridian_partition.embed.voyageai import VoyageAIEmbeddingEncoder

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
    "meridian_partition.ingest will be removed in a future version. "
    "Functionality moved to the unstructured-ingest project.",
    DeprecationWarning,
    stacklevel=2,
)
