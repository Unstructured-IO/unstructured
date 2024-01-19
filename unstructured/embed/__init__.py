from unstructured.embed.bedrock import BedrockEmbeddingEncoder
from unstructured.embed.huggingface import HuggingFaceEmbeddingEncoder
from unstructured.embed.openai import OpenAIEmbeddingEncoder
from unstructured.embed.octoai import OctoAIEmbeddingEncoder

EMBEDDING_PROVIDER_TO_CLASS_MAP = {
    "langchain-openai": OpenAIEmbeddingEncoder,
    "langchain-huggingface": HuggingFaceEmbeddingEncoder,
    "langchain-aws-bedrock": BedrockEmbeddingEncoder,
    "langchain-octoai": OctoAIEmbeddingEncoder,
}
