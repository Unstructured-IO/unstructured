import os

from unstructured.documents.elements import Text
from unstructured.embed.octoai import OctoAiEmbeddingConfig, OctoAIEmbeddingEncoder

embedding_encoder = OctoAIEmbeddingEncoder(
    config=OctoAiEmbeddingConfig(api_key=os.environ["OCTOAI_TOKEN"])
)
elements = embedding_encoder.embed_documents(
    elements=[Text("This is sentence 1"), Text("This is sentence 2")],
)

query = "This is the query"
query_embedding = embedding_encoder.embed_query(query=query)

[print(e.embeddings, e) for e in elements]
print(query_embedding, query)
print(embedding_encoder.is_unit_vector(), embedding_encoder.num_of_dimensions())
