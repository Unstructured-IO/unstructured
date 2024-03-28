import os

from unstructured.documents.elements import Text
from unstructured.embed.vertexai import VertexAIEmbeddingConfig, VertexAIEmbeddingEncoder

# To use Vertex AI PaLM tou will need to:
# - either, pass the full json content of your GCP VertexAI application credentials to the
# VertexAIEmbeddingConfig as the api_key parameter. (This will create a file in the ``/tmp``
# directory with the content of the json, and set the GOOGLE_APPLICATION_CREDENTIALS environment
# variable to the **path** of the created file.)
# - or, you'll need to store the path to a manually created service account JSON file as the
# GOOGLE_APPLICATION_CREDENTIALS environment variable. (For more information:
# https://python.langchain.com/docs/integrations/text_embedding/google_vertex_ai_palm)
# - or, you'll need to have the credentials configured for your environment (gcloud,
# workload identity, etc…)

embedding_encoder = VertexAIEmbeddingEncoder(
    config=VertexAIEmbeddingConfig(api_key=os.environ["VERTEXAI_GCP_APP_CREDS_JSON_CONTENT"])
)

elements = embedding_encoder.embed_documents(
    elements=[Text("This is sentence 1"), Text("This is sentence 2")],
)

query = "This is the query"
query_embedding = embedding_encoder.embed_query(query=query)

[print(e.embeddings, e) for e in elements]
print(query_embedding, query)
print(embedding_encoder.is_unit_vector(), embedding_encoder.num_of_dimensions())
