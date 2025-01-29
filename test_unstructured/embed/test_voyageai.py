from unittest.mock import Mock

from unstructured.documents.elements import Text
from unstructured.embed.voyageai import VoyageAIEmbeddingConfig, VoyageAIEmbeddingEncoder


def test_embed_documents_does_not_break_element_to_dict(mocker):
    # Mocked client with the desired behavior for embed_documents
    embed_response = Mock()
    embed_response.embeddings = [[1], [2]]
    mock_client = mocker.MagicMock()
    mock_client.embed.return_value = embed_response

    # Mock get_client to return our mock_client
    mocker.patch.object(VoyageAIEmbeddingConfig, "get_client", return_value=mock_client)

    encoder = VoyageAIEmbeddingEncoder(
        config=VoyageAIEmbeddingConfig(api_key="api_key", model_name="voyage-3-large")
    )
    elements = encoder.embed_documents(
        elements=[Text("This is sentence 1"), Text("This is sentence 2")],
    )
    assert len(elements) == 2
    assert elements[0].to_dict()["text"] == "This is sentence 1"
    assert elements[1].to_dict()["text"] == "This is sentence 2"
