from unstructured.documents.elements import Text
from unstructured.embed.openai import OpenAIEmbeddingEncoder


def test_embed_documents_does_not_break_element_to_dict(mocker):
    mocker.patch(
        "langchain.embeddings.openai.OpenAIEmbeddings.embed_documents", return_value=[1, 2]
    )
    encoder = OpenAIEmbeddingEncoder(api_key="api_key")
    elements = encoder.embed_documents(
        elements=[Text("This is sentence 1"), Text("This is sentence 2")],
    )
    assert len(elements) == 2
    assert elements[0].to_dict()["text"] == "This is sentence 1"
    assert elements[1].to_dict()["text"] == "This is sentence 2"
