from unstructured.documents.elements import Text
from unstructured.embed.vertexai import VertexAIEmbeddingConfig, VertextAIEmbeddingEncoder

# https://python.langchain.com/docs/integrations/text_embedding/google_vertex_ai_palm
# To use Vertex AI PaLM you must either have credentials configured for your environment (gcloud,
# workload identity, etc…), or store the path to a service account JSON file as the
# GOOGLE_APPLICATION_CREDENTIALS environment variable.

# Or, you can pass the json content of your API key to the VertexAIEmbeddingConfig
# like this: VertexAIEmbeddingConfig(api_key_json=GOOGLE_APPLICATION_CREDENTIALS_JSON_CONTENT)
# this will create a file in the working directory with the content of the json, and set the
# GOOGLE_APPLICATION_CREDENTIALS environment variable to the path of the file.

embedding_encoder = VertextAIEmbeddingEncoder(config=VertexAIEmbeddingConfig())
elements = embedding_encoder.embed_documents(
    elements=[Text("This is sentence 1"), Text("This is sentence 2")],
)

query = "This is the query"
query_embedding = embedding_encoder.embed_query(query=query)

[print(e.embeddings, e) for e in elements]
print(query_embedding, query)
print(embedding_encoder.is_unit_vector(), embedding_encoder.num_of_dimensions())
