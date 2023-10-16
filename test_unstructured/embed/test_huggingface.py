from unstructured.documents.elements import Text
from unstructured.embed.huggingface import HuggingFaceEmbeddingEncoder

HF = HuggingFaceEmbeddingEncoder()


def test_embed_documents(mocker):
    # Mocked client with the desired behavior for embed_documents
    mock_client = mocker.MagicMock()
    mock_client.embed_documents.return_value = [1, 2]

    # Mock get_openai_client to return our mock_client
    mocker.patch.object(HuggingFaceEmbeddingEncoder, "initialize", return_value=mock_client)

    model = HuggingFaceEmbeddingEncoder()
    elements = model.embed_documents(
        elements=[Text("This is sentence 1"), Text("This is sentence 2")],
    )
    assert len(elements) == 2
    assert elements[0].to_dict()["text"] == "This is sentence 1"
    assert elements[1].to_dict()["text"] == "This is sentence 2"
    assert "embeddings" in elements[0].to_dict()
    assert "embeddings" in elements[1].to_dict()
