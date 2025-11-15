from unittest.mock import Mock

from unstructured.documents.elements import Text
from unstructured.embed.voyageai import VoyageAIEmbeddingConfig, VoyageAIEmbeddingEncoder


def test_embed_documents_does_not_break_element_to_dict(mocker):
    # Mocked client with the desired behavior for embed_documents
    embed_response = Mock()
    embed_response.embeddings = [[1], [2]]
    mock_client = mocker.MagicMock()
    mock_client.embed.return_value = embed_response
    mock_client.tokenize.return_value = [[1], [1]]  # Mock token counts

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


def test_embed_documents_voyage_3_5(mocker):
    """Test embedding with voyage-3.5 model."""
    embed_response = Mock()
    embed_response.embeddings = [[1.0] * 1024, [2.0] * 1024]
    mock_client = mocker.MagicMock()
    mock_client.embed.return_value = embed_response
    mock_client.tokenize.return_value = [[1, 2, 3], [1, 2]]  # Mock token counts

    mocker.patch.object(VoyageAIEmbeddingConfig, "get_client", return_value=mock_client)

    encoder = VoyageAIEmbeddingEncoder(
        config=VoyageAIEmbeddingConfig(api_key="api_key", model_name="voyage-3.5")
    )
    elements = encoder.embed_documents(
        elements=[Text("Test document 1"), Text("Test document 2")],
    )
    assert len(elements) == 2
    assert len(elements[0].embeddings) == 1024
    assert len(elements[1].embeddings) == 1024


def test_embed_documents_voyage_3_5_lite(mocker):
    """Test embedding with voyage-3.5-lite model."""
    embed_response = Mock()
    embed_response.embeddings = [[1.0] * 512, [2.0] * 512, [3.0] * 512]
    mock_client = mocker.MagicMock()
    mock_client.embed.return_value = embed_response
    mock_client.tokenize.return_value = [[1], [1], [1]]  # Mock token counts

    mocker.patch.object(VoyageAIEmbeddingConfig, "get_client", return_value=mock_client)

    encoder = VoyageAIEmbeddingEncoder(
        config=VoyageAIEmbeddingConfig(api_key="api_key", model_name="voyage-3.5-lite")
    )
    elements = encoder.embed_documents(
        elements=[Text("Test 1"), Text("Test 2"), Text("Test 3")],
    )
    assert len(elements) == 3
    assert all(len(e.embeddings) == 512 for e in elements)


def test_embed_documents_contextual_model(mocker):
    """Test embedding with voyage-context-3 model."""
    # Mock contextualized_embed response
    contextualized_response = Mock()
    result_item = Mock()
    result_item.embeddings = [[1.0] * 1024, [2.0] * 1024]
    contextualized_response.results = [result_item]

    mock_client = mocker.MagicMock()
    mock_client.contextualized_embed.return_value = contextualized_response
    mock_client.tokenize.return_value = [[1, 2], [1, 2, 3]]  # Mock token counts

    mocker.patch.object(VoyageAIEmbeddingConfig, "get_client", return_value=mock_client)

    encoder = VoyageAIEmbeddingEncoder(
        config=VoyageAIEmbeddingConfig(api_key="api_key", model_name="voyage-context-3")
    )
    elements = encoder.embed_documents(
        elements=[Text("Context document 1"), Text("Context document 2")],
    )
    assert len(elements) == 2
    assert len(elements[0].embeddings) == 1024
    assert len(elements[1].embeddings) == 1024
    # Verify contextualized_embed was called
    mock_client.contextualized_embed.assert_called_once()


def test_count_tokens(mocker):
    """Test token counting functionality."""
    mock_client = mocker.MagicMock()
    mock_client.tokenize.return_value = [[1, 2], [1, 2, 3, 4, 5]]  # Different token counts

    mocker.patch.object(VoyageAIEmbeddingConfig, "get_client", return_value=mock_client)

    encoder = VoyageAIEmbeddingEncoder(
        config=VoyageAIEmbeddingConfig(api_key="api_key", model_name="voyage-3.5")
    )
    texts = ["short text", "this is a longer text with more tokens"]
    token_counts = encoder.count_tokens(texts)

    assert len(token_counts) == 2
    assert token_counts[0] == 2
    assert token_counts[1] == 5


def test_count_tokens_empty_list(mocker):
    """Test token counting with empty list."""
    mocker.patch.object(VoyageAIEmbeddingConfig, "get_client", return_value=mocker.MagicMock())

    encoder = VoyageAIEmbeddingEncoder(
        config=VoyageAIEmbeddingConfig(api_key="api_key", model_name="voyage-3.5")
    )
    token_counts = encoder.count_tokens([])
    assert token_counts == []


def test_get_token_limit(mocker):
    """Test getting token limit for different models."""
    mocker.patch.object(VoyageAIEmbeddingConfig, "get_client", return_value=mocker.MagicMock())

    # Test voyage-3.5 model
    config = VoyageAIEmbeddingConfig(api_key="api_key", model_name="voyage-3.5")
    assert config.get_token_limit() == 320_000

    # Test voyage-3.5-lite model
    config_lite = VoyageAIEmbeddingConfig(api_key="api_key", model_name="voyage-3.5-lite")
    assert config_lite.get_token_limit() == 1_000_000

    # Test context model
    config_context = VoyageAIEmbeddingConfig(api_key="api_key", model_name="voyage-context-3")
    assert config_context.get_token_limit() == 32_000

    # Test voyage-2 model
    config_v2 = VoyageAIEmbeddingConfig(api_key="api_key", model_name="voyage-2")
    assert config_v2.get_token_limit() == 320_000

    # Test unknown model (should use default)
    config_unknown = VoyageAIEmbeddingConfig(api_key="api_key", model_name="unknown-model")
    assert config_unknown.get_token_limit() == 120_000


def test_is_context_model(mocker):
    """Test the _is_context_model helper method."""
    mocker.patch.object(VoyageAIEmbeddingConfig, "get_client", return_value=mocker.MagicMock())

    # Test with context model
    encoder_context = VoyageAIEmbeddingEncoder(
        config=VoyageAIEmbeddingConfig(api_key="api_key", model_name="voyage-context-3")
    )
    assert encoder_context._is_context_model() is True

    # Test with regular model
    encoder_regular = VoyageAIEmbeddingEncoder(
        config=VoyageAIEmbeddingConfig(api_key="api_key", model_name="voyage-3.5")
    )
    assert encoder_regular._is_context_model() is False


def test_build_batches_with_token_limits(mocker):
    """Test that batching respects token limits."""
    mock_client = mocker.MagicMock()
    # Simulate different token counts for each text
    mock_client.tokenize.return_value = [[1] * 10, [1] * 20, [1] * 15, [1] * 25]

    mocker.patch.object(VoyageAIEmbeddingConfig, "get_client", return_value=mock_client)

    encoder = VoyageAIEmbeddingEncoder(
        config=VoyageAIEmbeddingConfig(api_key="api_key", model_name="voyage-2")
    )
    texts = ["text1", "text2", "text3", "text4"]
    batches = list(encoder._build_batches(texts, mock_client))

    # Should create at least one batch
    assert len(batches) >= 1
    # Total texts should be preserved
    total_texts = sum(len(batch) for batch in batches)
    assert total_texts == len(texts)


def test_embed_query(mocker):
    """Test embedding a single query."""
    embed_response = Mock()
    embed_response.embeddings = [[1.0] * 1024]
    mock_client = mocker.MagicMock()
    mock_client.embed.return_value = embed_response

    mocker.patch.object(VoyageAIEmbeddingConfig, "get_client", return_value=mock_client)

    encoder = VoyageAIEmbeddingEncoder(
        config=VoyageAIEmbeddingConfig(api_key="api_key", model_name="voyage-3.5")
    )
    embedding = encoder.embed_query("test query")

    assert len(embedding) == 1024
    # Verify embed was called with input_type="query"
    mock_client.embed.assert_called_once()
    call_kwargs = mock_client.embed.call_args[1]
    assert call_kwargs["input_type"] == "query"


def test_embed_documents_with_output_dimension(mocker):
    """Test embedding with custom output dimension."""
    embed_response = Mock()
    embed_response.embeddings = [[1.0] * 512, [2.0] * 512]
    mock_client = mocker.MagicMock()
    mock_client.embed.return_value = embed_response
    mock_client.tokenize.return_value = [[1], [1]]

    mocker.patch.object(VoyageAIEmbeddingConfig, "get_client", return_value=mock_client)

    encoder = VoyageAIEmbeddingEncoder(
        config=VoyageAIEmbeddingConfig(
            api_key="api_key", model_name="voyage-3.5", output_dimension=512
        )
    )
    elements = encoder.embed_documents(
        elements=[Text("Test 1"), Text("Test 2")],
    )
    assert len(elements) == 2
    # Verify output_dimension was passed
    call_kwargs = mock_client.embed.call_args[1]
    assert call_kwargs["output_dimension"] == 512


def test_embed_documents_empty_list(mocker):
    """Test embedding empty list of documents."""
    mocker.patch.object(VoyageAIEmbeddingConfig, "get_client", return_value=mocker.MagicMock())

    encoder = VoyageAIEmbeddingEncoder(
        config=VoyageAIEmbeddingConfig(api_key="api_key", model_name="voyage-3.5")
    )
    elements = encoder.embed_documents(elements=[])
    assert elements == []
