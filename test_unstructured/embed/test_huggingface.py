from unstructured.embed.huggingface import HuggingFaceEmbeddingEncoder

HF = HuggingFaceEmbeddingEncoder()


def test_embed_documents():
    model = HuggingFaceEmbeddingEncoder()
    elements = model.embed_documents(
        elements=[Text("This is sentence 1"), Text("This is sentence 2")],
    )
    assert len(elements) == 2
    assert elements[0].to_dict()["text"] == "This is sentence 1"
    assert elements[1].to_dict()["text"] == "This is sentence 2"
    assert "embeddings" in elements[0].to_dict()
    assert "embeddings" in elements[1].to_dict()
