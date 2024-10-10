from unstructured.documents.elements import Text
from unstructured.embed.mixedbreadai import (
    MixedbreadAIEmbeddingConfig,
    MixedbreadAIEmbeddingEncoder,
)


def test_embed_documents_does_not_break_element_to_dict(mocker):
    mock_client = mocker.MagicMock()

    def mock_embeddings(
        model,
        normalized,
        encoding_format,
        truncation_strategy,
        request_options,
        input,
    ):
        mock_response = mocker.MagicMock()
        mock_response.data = [mocker.MagicMock(embedding=[i, i + 1]) for i in range(len(input))]
        return mock_response

    mock_client.embeddings.side_effect = mock_embeddings

    # Mock get_client to return our mock_client
    mocker.patch.object(MixedbreadAIEmbeddingConfig, "get_client", return_value=mock_client)

    encoder = MixedbreadAIEmbeddingEncoder(
        config=MixedbreadAIEmbeddingConfig(
            api_key="api_key", model_name="mixedbread-ai/mxbai-embed-large-v1"
        )
    )

    elements = encoder.embed_documents(
        elements=[Text("This is sentence 1"), Text("This is sentence 2")],
    )
    assert len(elements) == 2
    assert elements[0].to_dict()["text"] == "This is sentence 1"
    assert elements[1].to_dict()["text"] == "This is sentence 2"
    assert elements[0].embeddings is not None
    assert elements[1].embeddings is not None
