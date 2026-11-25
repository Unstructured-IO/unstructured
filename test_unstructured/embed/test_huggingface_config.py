import pytest
from pydantic import ValidationError

from unstructured.embed.huggingface import HuggingFaceEmbeddingConfig


@pytest.mark.parametrize(
    "cache_folder", ["/models/cache", "relative/cache", "C:\\models\\cache", "模型缓存"]
)
def test_huggingface_config_accepts_cache_directory_strings(cache_folder):
    config = HuggingFaceEmbeddingConfig(cache_folder=cache_folder)

    assert config.cache_folder == cache_folder
    assert config.model_dump()["cache_folder"] == cache_folder


@pytest.mark.parametrize("kwargs", [{}, {"cache_folder": None}])
def test_huggingface_config_leaves_the_cache_directory_optional(kwargs):
    assert HuggingFaceEmbeddingConfig(**kwargs).cache_folder is None


def test_huggingface_config_rejects_a_mapping_as_a_cache_directory():
    with pytest.raises(ValidationError, match="cache_folder"):
        HuggingFaceEmbeddingConfig(cache_folder={"path": "/models/cache"})
