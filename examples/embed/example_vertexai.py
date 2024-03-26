from unstructured.documents.elements import Text
from unstructured.embed.vertexai import VertexAIEmbeddingConfig, VertextAIEmbeddingEncoder

# https://python.langchain.com/docs/integrations/text_embedding/google_vertex_ai_palm
# To use Vertex AI PaLM you must either have credentials configured for your environment (gcloud,
# workload identity, etc…), or store the path to a service account JSON file as the
# GOOGLE_APPLICATION_CREDENTIALS environment variable.

embedding_encoder = VertextAIEmbeddingEncoder(config=VertexAIEmbeddingConfig())
elements = embedding_encoder.embed_documents(
    elements=[Text("This is sentence 1"), Text("This is sentence 2")],
)

query = "This is the query"
query_embedding = embedding_encoder.embed_query(query=query)

[print(e.embeddings, e) for e in elements]
print(query_embedding, query)
print(embedding_encoder.is_unit_vector(), embedding_encoder.num_of_dimensions())
