from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from pydantic import ValidationError

from unstructured.documents.elements import Text
from unstructured.embed.voyageai import (
    MAX_BATCH_SIZE,
    VoyageAIEmbeddingConfig,
    VoyageAIEmbeddingEncoder,
)


@pytest.mark.parametrize("model_name", ["voyage-3.5", "voyage-context-3"])
@pytest.mark.parametrize("batch_size", [1, 2, 4])
def test_document_requests_honor_configured_batch_size(mocker, model_name, batch_size):
    client = Mock()
    client.tokenize.return_value = [[1] for _ in range(7)]
    client.embed.side_effect = lambda **kwargs: SimpleNamespace(
        embeddings=[[float(text)] for text in kwargs["texts"]]
    )
    client.contextualized_embed.side_effect = lambda **kwargs: SimpleNamespace(
        results=[SimpleNamespace(embeddings=[[float(text)] for text in kwargs["inputs"][0]])]
    )
    mocker.patch.object(VoyageAIEmbeddingConfig, "get_client", return_value=client)
    encoder = VoyageAIEmbeddingEncoder(
        config=VoyageAIEmbeddingConfig(
            api_key="unused", model_name=model_name, batch_size=batch_size
        )
    )
    elements = [Text(str(index)) for index in range(7)]

    result = encoder.embed_documents(elements)

    calls = (
        client.contextualized_embed.call_args_list
        if model_name == "voyage-context-3"
        else client.embed.call_args_list
    )
    batches = [
        call.kwargs["inputs"][0] if model_name == "voyage-context-3" else call.kwargs["texts"]
        for call in calls
    ]
    assert [len(batch) for batch in batches] == [
        min(batch_size, len(elements) - start) for start in range(0, len(elements), batch_size)
    ]
    assert [text for batch in batches for text in batch] == [element.text for element in elements]
    assert all(result[index] is element for index, element in enumerate(elements))
    assert [element.embeddings for element in result] == [[float(index)] for index in range(7)]


@pytest.mark.parametrize("batch_size", [None, MAX_BATCH_SIZE * 2])
def test_default_and_large_batch_sizes_keep_the_existing_provider_cap(batch_size):
    client = Mock()
    texts = [str(index) for index in range(MAX_BATCH_SIZE + 2)]
    client.tokenize.return_value = [[1] for _ in texts]
    encoder = VoyageAIEmbeddingEncoder(
        config=VoyageAIEmbeddingConfig(
            api_key="unused", model_name="voyage-3.5", batch_size=batch_size
        )
    )

    batches = list(encoder._build_batches(texts, client))

    assert [len(batch) for batch in batches] == [MAX_BATCH_SIZE, 2]
    assert [text for batch in batches for text in batch] == texts


def test_configured_batch_size_also_respects_the_token_limit(mocker):
    client = Mock()
    client.tokenize.return_value = [[1], [1], [1] * 4, [1], [1]]
    mocker.patch.object(VoyageAIEmbeddingConfig, "get_token_limit", return_value=4)
    encoder = VoyageAIEmbeddingEncoder(
        config=VoyageAIEmbeddingConfig(api_key="unused", model_name="voyage-3.5", batch_size=2)
    )

    assert list(encoder._build_batches(["a", "b", "c", "d", "e"], client)) == [
        ["a", "b"],
        ["c"],
        ["d", "e"],
    ]


@pytest.mark.parametrize("batch_size", [0, -1])
def test_nonpositive_batch_sizes_are_rejected_at_configuration_time(batch_size):
    with pytest.raises(ValidationError, match="batch_size"):
        VoyageAIEmbeddingConfig(api_key="unused", model_name="voyage-3.5", batch_size=batch_size)
