import os

from unstructured.documents.elements import Text
from unstructured.embed.openai import OpenAIEmbeddingEncoder

embedding_encoder = OpenAIEmbeddingEncoder(api_key=os.environ["OPENAI_API_KEY"])
elements = embedding_encoder.embed(
    elements=[Text("This is sentence 1"), Text("This is sentence 2")],
)

[print(e.embeddings, e) for e in elements]
