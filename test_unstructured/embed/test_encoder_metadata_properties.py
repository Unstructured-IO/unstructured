from types import SimpleNamespace

import pytest

from unstructured.embed.octoai import OctoAiEmbeddingConfig, OctoAIEmbeddingEncoder
from unstructured.embed.openai import OpenAIEmbeddingConfig, OpenAIEmbeddingEncoder
from unstructured.embed.vertexai import VertexAIEmbeddingConfig, VertexAIEmbeddingEncoder


@pytest.fixture(
    params=[
        (OpenAIEmbeddingEncoder, OpenAIEmbeddingConfig),
        (VertexAIEmbeddingEncoder, VertexAIEmbeddingConfig),
        (OctoAIEmbeddingEncoder, OctoAiEmbeddingConfig),
    ],
    ids=["openai", "vertexai", "octoai"],
)
def make_encoder(request, mocker):
    encoder_type, config_type = request.param

    def create(vector):
        client = mocker.MagicMock()
        client.embed_query.return_value = vector
        client.embeddings.create.return_value = SimpleNamespace(
            data=[SimpleNamespace(embedding=vector)]
        )
        mocker.patch.object(config_type, "get_client", return_value=client)
        return encoder_type(config=config_type(api_key="test-key"))

    return create


def test_embedding_dimension_metadata_is_a_value_through_the_base_interface(make_encoder):
    encoder = make_encoder([3.0, 4.0, 0.0])

    assert encoder.num_of_dimensions == (3,)


@pytest.mark.parametrize(
    ("vector", "expected"),
    [([0.6, 0.8], True), ([3.0, 4.0, 0.0], False), ([0.0, 0.0], False)],
    ids=["unit", "non-unit", "zero"],
)
def test_unit_vector_property_reports_vector_data_instead_of_a_truthy_method(
    make_encoder, vector, expected
):
    encoder = make_encoder(vector)

    result = encoder.is_unit_vector
    assert not callable(result)
    assert bool(result) is expected


def test_query_embedding_remains_available(make_encoder):
    vector = [0.1, 0.2, 0.3]
    encoder = make_encoder(vector)

    assert encoder.embed_query("document query") == vector
