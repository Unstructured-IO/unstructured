import contextlib
import json

import httpx
import pytest

from unstructured.documents.elements import Text
from unstructured.embed.mixedbreadai import (
    MixedbreadAIEmbeddingConfig,
    MixedbreadAIEmbeddingEncoder,
)


@pytest.fixture
def make_encoder(mocker):
    sdk = pytest.importorskip("mixedbread_ai.client")
    with contextlib.ExitStack() as stack:

        def create(*, reverse=False, indices=None):
            batches = []

            def respond(request):
                assert request.url.path == "/v1/embeddings"
                payload = json.loads(request.content)
                batch = payload["input"]
                batches.append(batch)
                data = [
                    {"index": index, "embedding": [float(text) + 0.5]}
                    for index, text in enumerate(batch)
                ]
                if indices is not None:
                    data = [dict(item, index=index) for item, index in zip(data, indices)]
                if reverse:
                    data.reverse()
                return httpx.Response(
                    200,
                    json={
                        "data": data,
                        "model": payload["model"],
                        "normalized": True,
                        "encoding_format": "float",
                        "usage": {"prompt_tokens": len(batch), "total_tokens": len(batch)},
                    },
                )

            transport = stack.enter_context(httpx.Client(transport=httpx.MockTransport(respond)))
            client = sdk.MixedbreadAI(api_key="test", httpx_client=transport)
            mocker.patch.object(MixedbreadAIEmbeddingConfig, "get_client", return_value=client)
            return MixedbreadAIEmbeddingEncoder(
                MixedbreadAIEmbeddingConfig(api_key="test")
            ), batches

        yield create


@pytest.mark.parametrize("count", [2, 129])
@pytest.mark.parametrize("reverse", [False, True])
def test_document_embeddings_follow_response_indices_within_each_batch(
    make_encoder, count, reverse
):
    encoder, batches = make_encoder(reverse=reverse)
    elements = [Text(str(index)) for index in range(count)]

    result = encoder.embed_documents(elements)

    assert result is elements
    assert [element.embeddings for element in result] == [[index + 0.5] for index in range(count)]
    assert [len(batch) for batch in batches] == ([128, 1] if count == 129 else [2])


@pytest.mark.parametrize("indices", [[0, 0], [-1, 0], [0, 2], [0]])
def test_invalid_response_indices_do_not_attach_embeddings_to_documents(make_encoder, indices):
    encoder, _ = make_encoder(indices=indices)
    elements = [Text("0"), Text("1")]

    with pytest.raises(ValueError, match="response indices"):
        encoder.embed_documents(elements)

    assert all(element.embeddings is None for element in elements)
