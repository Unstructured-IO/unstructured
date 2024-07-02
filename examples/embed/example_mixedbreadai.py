import os

from unstructured.documents.elements import Text
from unstructured.embed.mixedbreadai import (
    MixedbreadAIEmbeddingConfig,
    MixedbreadAIEmbeddingEncoder,
)

# To use Mixedbread AI you will need to pass
# Mixedbread AI API Key (obtained from https://www.mixedbread.ai)
# as the ``api_key`` parameter.
#
# The ``model_name`` parameter is mandatory, please check the available models
# at https://www.mixedbread.ai/docs/embeddings/models#whats-new-in-the-mixedbread-embed-model-family

embedding_encoder = MixedbreadAIEmbeddingEncoder(
    config=MixedbreadAIEmbeddingConfig(
        api_key=os.environ.get("MXBAI_API_KEY", None),
        model_name="mixedbread-ai/mxbai-embed-large-v1",
    )
)

embedding_encoder.initialize()

# Embedding documents
elements = embedding_encoder.embed_documents(
    elements=[Text("This is sentence 1"), Text("This is sentence 2")]
)

# Embedding a query
query = "This is the query"
query_embedding = embedding_encoder.embed_query(query=query)

# Printing document embeddings
for e in elements:
    print(e, e.embeddings)

# Printing query embedding
print(query, query_embedding)

# Printing unit vector status and number of dimensions
print(embedding_encoder.is_unit_vector, embedding_encoder.num_of_dimensions)
