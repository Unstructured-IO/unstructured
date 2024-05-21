import os

from unstructured.documents.elements import Text
from unstructured.embed.voyageai import VoyageAIEmbeddingConfig, VoyageAIEmbeddingEncoder

# To use Voyage AI you will need to pass Voyage AI API Key (obtained from https://dash.voyageai.com/)
# as the ``api_key`` parameter.
#
# The ``model_name`` parameter is mandatory, please check the available models
# at https://docs.voyageai.com/docs/embeddings

embedding_encoder = VoyageAIEmbeddingEncoder(
    config=VoyageAIEmbeddingConfig(
        api_key=os.environ["VOYAGE_API_KEY"],
        model_name="voyage-law-2"
    )
)
elements = embedding_encoder.embed_documents(
    elements=[Text("This is sentence 1"), Text("This is sentence 2")],
)

query = "This is the query"
query_embedding = embedding_encoder.embed_query(query=query)

[print(e, e.embeddings) for e in elements]
print(query, query_embedding)
print(embedding_encoder.is_unit_vector, embedding_encoder.num_of_dimensions)
