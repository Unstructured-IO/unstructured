import numpy as np
import pytest

from unstructured.documents.elements import Text
from unstructured.embed import EMBEDDING_PROVIDER_TO_CLASS_MAP
from unstructured.embed.bedrock import BedrockEmbeddingConfig, BedrockEmbeddingEncoder


@pytest.fixture
def config():
    return BedrockEmbeddingConfig(
        aws_access_key_id="test-access-key", aws_secret_access_key="test-secret-key"
    )


@pytest.mark.parametrize(
    "encoder_type",
    [BedrockEmbeddingEncoder, EMBEDDING_PROVIDER_TO_CLASS_MAP["langchain-aws-bedrock"]],
    ids=["direct", "provider-registry"],
)
def test_bedrock_encoder_can_be_created_without_contacting_a_provider(encoder_type, config, mocker):
    get_client = mocker.patch.object(BedrockEmbeddingConfig, "get_client")

    encoder = encoder_type(config=config)

    assert encoder.config is config
    encoder.initialize()
    get_client.assert_not_called()


def test_bedrock_query_embedding_is_available_after_construction(config, mocker):
    client = mocker.MagicMock()
    client.embed_query.return_value = [0.1, 0.2, 0.3]
    mocker.patch.object(BedrockEmbeddingConfig, "get_client", return_value=client)

    encoder = BedrockEmbeddingEncoder(config=config)
    result = encoder.embed_query("Find this passage")

    np.testing.assert_array_equal(result, [0.1, 0.2, 0.3])
    client.embed_query.assert_called_once_with("Find this passage")


def test_bedrock_document_embeddings_remain_attached_to_original_elements(config, mocker):
    vectors = [[0.1, 0.2], [0.3, 0.4]]
    client = mocker.MagicMock()
    client.embed_documents.return_value = vectors
    mocker.patch.object(BedrockEmbeddingConfig, "get_client", return_value=client)
    elements = [Text("First passage"), Text("Second passage")]

    encoder = BedrockEmbeddingEncoder(config=config)
    result = encoder.embed_documents(elements)

    assert result is elements
    assert [element.to_dict()["embeddings"] for element in result] == vectors
    client.embed_documents.assert_called_once_with(["First passage", "Second passage"])
