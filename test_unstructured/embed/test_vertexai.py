from unstructured.documents.elements import Text
from unstructured.embed.vertexai import VertexAIEmbeddingConfig, VertexAIEmbeddingEncoder


def test_embed_documents_does_not_break_element_to_dict(mocker):
    # Mocked client with the desired behavior for embed_documents
    mock_client = mocker.MagicMock()
    mock_client.embed_documents.return_value = [1, 2]

    # Mock create_client to return our mock_client
    mocker.patch.object(VertexAIEmbeddingEncoder, "create_client", return_value=mock_client)

    encoder = VertexAIEmbeddingEncoder(config=VertexAIEmbeddingConfig(api_key="api_key"))
    elements = encoder.embed_documents(
        elements=[Text("This is sentence 1"), Text("This is sentence 2")],
    )
    assert len(elements) == 2
    assert elements[0].to_dict()["text"] == "This is sentence 1"
    assert elements[1].to_dict()["text"] == "This is sentence 2"
