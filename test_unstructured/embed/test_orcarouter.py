from unstructured.documents.elements import Text
from unstructured.embed.orcarouter import OrcaRouterEmbeddingConfig, OrcaRouterEmbeddingEncoder


def test_embed_documents_does_not_break_element_to_dict(mocker):
    # Mocked client with the desired behavior for embed_documents
    mock_client = mocker.MagicMock()
    mock_client.embed_documents.return_value = [1, 2]

    # Mock get_client to return our mock_client
    mocker.patch.object(OrcaRouterEmbeddingConfig, "get_client", return_value=mock_client)

    encoder = OrcaRouterEmbeddingEncoder(config=OrcaRouterEmbeddingConfig(api_key="api_key"))
    elements = encoder.embed_documents(
        elements=[Text("This is sentence 1"), Text("This is sentence 2")],
    )
    assert len(elements) == 2
    assert elements[0].to_dict()["text"] == "This is sentence 1"
    assert elements[1].to_dict()["text"] == "This is sentence 2"


def test_embed_query(mocker):
    # Mocked client whose embeddings.create returns an object with the expected shape
    mock_data_item = mocker.MagicMock()
    mock_data_item.embedding = [0.1, 0.2, 0.3]
    mock_response = mocker.MagicMock()
    mock_response.data = [mock_data_item]
    mock_client = mocker.MagicMock()
    mock_client.embeddings.create.return_value = mock_response

    mocker.patch.object(OrcaRouterEmbeddingConfig, "get_client", return_value=mock_client)

    encoder = OrcaRouterEmbeddingEncoder(config=OrcaRouterEmbeddingConfig(api_key="api_key"))
    embedding = encoder.embed_query("A sample query.")
    assert embedding == [0.1, 0.2, 0.3]
    mock_client.embeddings.create.assert_called_once_with(
        input="A sample query.",
        model="openai/text-embedding-3-small",
    )
